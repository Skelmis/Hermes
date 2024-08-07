import uuid

from piccolo.apps.user.tables import BaseUser
from piccolo.table import Table
from piccolo.columns import UUID, ForeignKey, Text, Integer, Boolean


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

    @property
    def uuid(self) -> str:
        return str(self.id)


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


# TODO Add status fields
class Vulnerability(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    scan = ForeignKey(
        Scan,
        index=True,
        help_text="The scan this vulnerability exists as",
    )
    title = Text()
    description = Text(default="")
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
