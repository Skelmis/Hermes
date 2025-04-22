import uuid

from litestar.response import Redirect
from piccolo.apps.user.tables import BaseUser
from piccolo.columns import UUID, Timestamptz, JSON, ForeignKey
from piccolo.table import Table


class Archives(Table, help_text="A read only import of a scan from an archive file."):
    # Heavy misuse of JSON columns as I don't want to have to type everything
    # + it leaves our schema open to easily support future schema changes
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    owner = ForeignKey(BaseUser, index=True, help_text="Who owns this archive")
    archive_created_at = Timestamptz(
        help_text="When the archive was originally created"
    )
    archive_creator = JSON()
    scan = JSON(help_text="The JSON related to the scan info")
    created_at = Timestamptz(help_text="When this was created")

    @property
    def uuid(self) -> str:
        return str(self.id)

    def redirect_to(self) -> Redirect:
        return Redirect(f"/archives/{self.uuid}")
