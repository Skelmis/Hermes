import os
from pathlib import Path

from commons import value_to_bool
from dotenv import load_dotenv
from piccolo.conf.apps import AppRegistry
from piccolo.engine import SQLiteEngine
from piccolo.engine.postgres import PostgresEngine
from saq import Queue

from home.analysis import AnalysisInterface, Bandit, Semgrep, GoSec

load_dotenv()

if not value_to_bool(os.environ.get("DEBUG")):
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

REGISTERED_INTERFACES: dict[str, type[AnalysisInterface]] = {
    Bandit.id: Bandit,
    Semgrep.id: Semgrep,
    GoSec.id: GoSec,
}
BASE_PROJECT_DIR: Path = Path(".projects")
BASE_PROJECT_DIR.mkdir(exist_ok=True)  # Ensure it exists


ALLOW_REGISTRATION: bool = value_to_bool(os.environ.get("ALLOW_REGISTRATION", True))
"""Whether users should be allowed to create new accounts."""


SAQ_QUEUE = Queue.from_url("redis://localhost")
