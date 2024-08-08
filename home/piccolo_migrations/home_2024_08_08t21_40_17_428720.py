from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from enum import Enum
from piccolo.columns.column_types import Text


ID = "2024-08-08T21:40:17:428720"
VERSION = "1.15.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="home", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="Notification",
        tablename="notification",
        column_name="level",
        db_column_name="level",
        params={
            "choices": Enum(
                "NotificationLevels",
                {
                    "INFO": "info",
                    "WARNING": "warning",
                    "ERROR": "error",
                    "SUCCESS": "success",
                },
            )
        },
        old_params={
            "choices": Enum(
                "NotificationLevels",
                {
                    "INFO": "info",
                    "WARNING": "warning",
                    "ERROR": "error",
                    "SUCCESS": "SUCCESS",
                },
            )
        },
        column_class=Text,
        old_column_class=Text,
        schema=None,
    )

    return manager
