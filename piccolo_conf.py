import os
from pathlib import Path

from apscheduler import AsyncScheduler
from dotenv import load_dotenv

from piccolo.engine import SQLiteEngine
from piccolo.engine.postgres import PostgresEngine
from piccolo.conf.apps import AppRegistry

from home.analysis import AnalysisInterface, Bandit, Semgrep

load_dotenv()

if os.environ.get("PROD", None) is not None:
    DB = PostgresEngine(
        config={
            "database": os.environ["POSTGRES_DB"],
            "user": os.environ["POSTGRES_USER"],
            "password": os.environ["POSTGRES_PASSWORD"],
            "host": os.environ["POSTGRES_HOST"],
            "port": int(os.environ["POSTGRES_PORT"]),
        },
        extensions=tuple(),
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
}
BASE_PROJECT_DIR: Path = Path(".projects")
BASE_PROJECT_DIR.mkdir(exist_ok=True)  # Ensure it exists

ASYNC_SCHEDULER: AsyncScheduler = AsyncScheduler()
