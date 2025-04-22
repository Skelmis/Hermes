import os

from dotenv import load_dotenv
from piccolo.conf.apps import AppRegistry
from piccolo.engine import SQLiteEngine
from piccolo.engine.postgres import PostgresEngine

load_dotenv()

if os.environ.get("POSTGRES_HOST", False):
    DB = PostgresEngine(
        config={
            "database": os.environ["POSTGRES_DB"],
            "user": os.environ["POSTGRES_USER"],
            "password": os.environ["POSTGRES_PASSWORD"],
            "host": os.environ["POSTGRES_HOST"],
            "port": int(os.environ["POSTGRES_PORT"]),
        },
    )
else:
    DB = SQLiteEngine()

APP_REGISTRY = AppRegistry(
    apps=[
        "home.piccolo_app",
        "piccolo_admin.piccolo_app",
        "piccolo_api.session_auth.piccolo_app",
        "piccolo.apps.user.piccolo_app",
    ]
)
