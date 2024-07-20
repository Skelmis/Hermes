import os

from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin

from home.controllers import ProjectController
from home.endpoints import home
from home.piccolo_app import APP_CONFIG
from litestar import Litestar, asgi
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.static_files import StaticFilesConfig
from litestar.template import TemplateConfig
from litestar.types import Receive, Scope, Send
from piccolo.engine import engine_finder
from piccolo_admin.endpoints import create_admin
from dotenv import load_dotenv

load_dotenv()


# mounting Piccolo Admin
@asgi("/admin/", is_mount=True)
async def admin(scope: "Scope", receive: "Receive", send: "Send") -> None:
    await create_admin(tables=APP_CONFIG.table_classes)(scope, receive, send)


async def open_database_connection_pool():
    try:
        engine = engine_finder()
        await engine.start_connection_pool()
    except Exception:
        print("Unable to connect to the database")


async def close_database_connection_pool():
    try:
        engine = engine_finder()
        await engine.close_connection_pool()
    except Exception:
        print("Unable to connect to the database")


app = Litestar(
    route_handlers=[admin, home, ProjectController],
    template_config=TemplateConfig(
        directory="home/templates", engine=JinjaTemplateEngine
    ),
    static_files_config=[
        StaticFilesConfig(directories=["static"], path="/static/"),
    ],
    on_startup=[open_database_connection_pool],
    on_shutdown=[close_database_connection_pool],
    debug=bool(os.environ.get("DEBUG", False)),
    openapi_config=OpenAPIConfig(
        title="Hermes API",
        version="0.0.0",
        render_plugins=[SwaggerRenderPlugin()],
        path="/docs",
    ),
)
