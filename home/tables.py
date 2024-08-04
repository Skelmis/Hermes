import uuid

from piccolo.apps.user.tables import BaseUser
from piccolo.table import Table
from piccolo.columns import UUID, ForeignKey, Text


class Project(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    owner = ForeignKey(BaseUser, help_text="Who owns this project")
    title = Text()
    description = Text(default="")

    @property
    def uuid(self) -> str:
        return str(self.id)


# TODO Add status fields
class Vulnerability(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    project = ForeignKey(
        Project,
        help_text="The project this vulnerability exists on",
    )
    title = Text()
    description = Text(default="")
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

    @property
    def uuid(self) -> str:
        return str(self.id)
