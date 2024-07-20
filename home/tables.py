import uuid

from piccolo.table import Table
from piccolo.columns import UUID


class Project(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
