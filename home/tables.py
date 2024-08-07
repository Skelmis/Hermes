import uuid
from typing import Type

from litestar.response import Redirect
from piccolo.apps.user.tables import BaseUser
from piccolo.table import Table
from piccolo.columns import UUID, ForeignKey, Text, Integer, Boolean, Array

from home.util.flash import alert


class Project(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    owner = ForeignKey(BaseUser, index=True, help_text="Who owns this project")
    title = Text()
    description = Text(default="")
    directory = Text(default="", help_text="The path to this project on disk")
    is_git_based = Boolean(
        default=False,
        help_text="Denotes if the underlying stuff is git based "
        "and is used as a check before performing git actions",
    )
    code_scanners = Array(
        base_column=Text(),
        help_text="A list of Analysis Interface id's to use",
    )

    @property
    def scanner_path(self) -> str:
        """The path input to a given scanner"""
        from piccolo_conf import BASE_PROJECT_DIR

        return str(BASE_PROJECT_DIR / self.directory)

    def normalize_finding_path(self, file_path: str) -> str:
        """Remove the metadata paths from findings"""
        return file_path.removeprefix(f"{self.scanner_path}/")

    @property
    def uuid(self) -> str:
        return str(self.id)

    async def run_scanners(self, request) -> Redirect:
        """Run all the relevant scanners for this project"""
        from piccolo_conf import REGISTERED_INTERFACES
        from home.analysis import AnalysisInterface

        fail_count = 0
        for interface_id in self.code_scanners:
            interface: Type[AnalysisInterface] | None = REGISTERED_INTERFACES.get(
                interface_id
            )
            if interface is None:
                alert(
                    request,
                    f"Failed to find an interface with id {interface_id}",
                    level="error",
                )
                fail_count += 1
                continue

            instance = interface(self)
            await instance.scan()

        if fail_count == len(self.code_scanners):
            alert(
                request,
                "Looks like all interfaces could not be found. Ran nothing",
                level="error",
            )
        else:
            alert(
                request,
                "Successfully ran found scanners",
                level="success",
            )

        return Redirect(f"/projects/{self.uuid}")


class Scan(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    project = ForeignKey(
        Project,
        index=True,
        help_text="The project this scan was run for",
    )
    number = Integer(
        index=True,
        help_text="What number scan this is, in relation to a specific project",
    )

    @property
    def uuid(self) -> str:
        return str(self.id)

    @classmethod
    async def get_next_number(cls, project: Project) -> int:
        """Fetches the next scan number for a given project"""
        count = await Scan.count().where(Scan.project == project)
        return count + 1


# TODO Add status fields
class Vulnerability(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    scan = ForeignKey(
        Scan,
        index=True,
        help_text="The scan this vulnerability exists as",
    )
    project = ForeignKey(
        Project,
        index=True,
        help_text="The project this vulnerability belongs to",
    )
    title = Text()
    description = Text(default="")
    impact = Text(default="", help_text="The scanner disclosed impact of this result")
    likelihood = Text(
        default="", help_text="The scanner disclosed likelihood of this result"
    )
    severity = Text(
        default="", help_text="The scanner disclosed severity of this result"
    )
    confidence = Text(
        default="", help_text="How confident the scanner is about this result"
    )
    code_file = Text(
        default="",
        help_text="A path to the code at fault",
    )
    code_line = Text(
        default="",
        help_text="The line of code which threw this error",
    )
    code_context = Text(
        default="",
        help_text="The code related to this issue",
    )
    found_by = Text(
        default="Unknown",
        help_text="The analysis interface that found this vulnerability",
    )

    @property
    def uuid(self) -> str:
        return str(self.id)
