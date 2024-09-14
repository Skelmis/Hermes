from __future__ import annotations

import datetime
import logging
import subprocess
import uuid
from typing import Type

import commons
from litestar.response import Redirect
from piccolo.apps.user.tables import BaseUser
from piccolo.columns import (
    UUID,
    ForeignKey,
    Text,
    Boolean,
    Array,
    Timestamptz,
    Serial,
    Where,
    Or,
)
from piccolo.query import Query
from piccolo.table import Table

from home.tables import ProjectAutomation, Notification, Scan

log = logging.getLogger(__name__)


class Project(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    owner = ForeignKey(BaseUser, index=True, help_text="Who owns this project")
    created_at = Timestamptz(help_text="When the project was created")
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
    is_public: bool = Boolean(
        default=False,
        help_text="Should anyone be able to see and interact with this project?",
    )
    other_users: list[BaseUser] = Array(
        base_column=Serial(),
        help_text="Other users who should have access to this. "
        "Defaults to user id since array foreign keys aren't allowed and i dont wanna do M2M",
    )

    @classmethod
    def add_ownership_where(cls, query, user: BaseUser):
        """Add a where clause to ensure the user can see this project"""
        return query.where(
            Or(
                Project.owner == user,
                Or(Project.is_public == True, Project.other_users.any(user.id)),  # type: ignore
            )
        )

    @property
    def short_description(self) -> str:
        return (
            f"{self.description[:47]}..."
            if self.description and len(self.description) > 47
            else self.description
        )

    @property
    def scanner_path(self) -> str:
        """The path input to a given scanner"""
        from piccolo_conf import BASE_PROJECT_DIR

        return str(BASE_PROJECT_DIR / self.directory)

    def normalize_finding_path(self, file_path: str) -> str:
        """Remove the metadata paths from findings"""
        output = file_path.removeprefix(f"{self.scanner_path}/")
        if self.scanner_path in output:
            # Maybe its absolute path'd it
            _, output = file_path.split(self.scanner_path)
            output = output.removeprefix("/")

        return output

    @property
    def uuid(self) -> str:
        return str(self.id)

    def redirect_to(self) -> Redirect:
        return Redirect(f"/projects/{self.uuid}")

    async def get_associated_automation(self) -> ProjectAutomation | None:
        return (
            await ProjectAutomation.objects()
            .where(ProjectAutomation.project == self)
            .first()
        )

    async def get_last_scan(self) -> Scan | None:
        return (
            await Scan.objects()
            .where(Scan.project == self)
            .order_by(Scan.number, ascending=False)
            .first()
        )

    async def update_from_source(self, request) -> None:
        """Updates the underlying source code

        Notes
        -----
        Designed to be run in the background
        due to how long it may take
        """
        if not self.is_git_based:
            raise ValueError("Cannot update a non git based project")

        fetch = ["git", "fetch"]
        pull = ["git", "pull"]
        try:
            # TODO Move these to anyio
            subprocess.check_output(fetch, cwd=self.scanner_path)
            subprocess.check_output(pull, cwd=self.scanner_path)
        except Exception as e:
            await Notification.create_alert(
                request.user,
                f"Something went wrong pulling project '{self.title}', check the logs",
                level="error",
            )
            log.error("Git cloning died with error\n%s", commons.exception_as_string(e))
        else:
            pa: ProjectAutomation | None = await self.get_associated_automation()
            if pa:
                pa.last_pulled_at = datetime.datetime.now(tz=datetime.timezone.utc)
                await pa.save()

        await Notification.create_alert(
            request.user,
            f"Successfully pulled project '{self.title}'",
            level="success",
        )

    async def run_scanners(self, request) -> Redirect:
        """Run all the relevant scanners for this project.

        Notes
        -----
        Designed to be run in the background
        due to how long it may take
        """
        from piccolo_conf import REGISTERED_INTERFACES
        from home.analysis import AnalysisInterface

        fail_count = 0
        scan = Scan(
            project=self,
            number=await Scan.get_next_number(self),
        )
        await scan.save()
        for interface_id in self.code_scanners:
            interface: Type[AnalysisInterface] | None = REGISTERED_INTERFACES.get(
                interface_id
            )
            if interface is None:
                await Notification.create_alert(
                    request.user,
                    f"Failed to find an interface with id {interface_id}",
                    level="error",
                )
                fail_count += 1
                continue

            instance = interface(self)
            try:
                await instance.scan(scan)
            except Exception as e:
                await Notification.create_alert(
                    request.user,
                    f"Interface {interface_id} failed to run",
                    level="error",
                )
                fail_count += 1
                print(commons.exception_as_string(e))

        if fail_count == len(self.code_scanners):
            await Notification.create_alert(
                request.user,
                f"Looks like all interfaces could not be found."
                f" Ran nothing for project '{self.title}'",
                level="error",
            )
        else:
            await Notification.create_alert(
                request.user,
                f"Successfully ran found scanners against project '{self.title}'",
                level="success",
            )

        pa: ProjectAutomation | None = await self.get_associated_automation()
        if pa:
            pa.last_scanned_at = datetime.datetime.now(tz=datetime.timezone.utc)
            await pa.save()

        return Redirect(f"/projects/{self.uuid}")
