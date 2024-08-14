from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from enum import Enum
from piccolo.columns.column_types import Text
from piccolo.columns.indexes import IndexMethod


ID = "2024-08-14T20:04:56:987874"
VERSION = "1.16.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="home", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="Vulnerability",
        tablename="vulnerability",
        column_name="state",
        db_column_name="state",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "New",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": Enum(
                "VulnerabilityState",
                {
                    "NEW": "New",
                    "EXPLOITABLE": "Exploitable",
                    "UNDER_TRIAGE": "Under Triage",
                    "NOT_EXPLOITABLE": "Not Exploitable",
                },
            ),
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    return manager
