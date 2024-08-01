import uuid

from piccolo.apps.user.tables import BaseUser
from piccolo.table import Table
from piccolo.columns import UUID, ForeignKey


class Project(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    owner = ForeignKey(BaseUser, unique=True, help_text="Who owns this project")
