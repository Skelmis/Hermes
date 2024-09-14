from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Array
from piccolo.columns.column_types import Serial, Integer
from piccolo.columns.indexes import IndexMethod


ID = "2024-09-14T21:09:56:790331"
VERSION = "1.17.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="home", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="Project",
        tablename="project",
        column_name="other_users",
        db_column_name="other_users",
        params={
            "base_column": Integer(
                default=0,
                null=False,
                primary_key=False,
                unique=False,
                index=False,
                index_method=IndexMethod.btree,
                choices=None,
                db_column_name=None,
                secret=False,
            )
        },
        old_params={
            "base_column": Serial(
                null=False,
                primary_key=False,
                unique=False,
                index=False,
                index_method=IndexMethod.btree,
                choices=None,
                db_column_name=None,
                secret=False,
            )
        },
        column_class=Array,
        old_column_class=Array,
        schema=None,
    )

    return manager
