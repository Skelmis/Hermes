from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from enum import Enum
from piccolo.columns.column_types import Text
from piccolo.columns.indexes import IndexMethod


ID = "2024-08-14T20:09:39:553451"
VERSION = "1.16.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="home", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="Vulnerability",
        tablename="vulnerability",
        column_name="exploitability",
        db_column_name="exploitability",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "Unknown",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": Enum(
                "VulnerabilityExploitability",
                {
                    "UNKNOWN": "Unknown",
                    "EXPLOITABLE": "Exploitable",
                    "NOT_EXPLOITABLE": "Not Exploitable",
                },
            ),
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.alter_column(
        table_class_name="Vulnerability",
        tablename="vulnerability",
        column_name="state",
        db_column_name="state",
        params={
            "index": True,
            "choices": Enum(
                "VulnerabilityState",
                {
                    "NEW": "New",
                    "UNDER_TRIAGE": "Under Triage",
                    "RESOLVED": "Resolved",
                },
            ),
        },
        old_params={
            "index": False,
            "choices": Enum(
                "VulnerabilityState",
                {
                    "NEW": "New",
                    "EXPLOITABLE": "Exploitable",
                    "UNDER_TRIAGE": "Under Triage",
                    "NOT_EXPLOITABLE": "Not Exploitable",
                },
            ),
        },
        column_class=Text,
        old_column_class=Text,
        schema=None,
    )

    return manager
