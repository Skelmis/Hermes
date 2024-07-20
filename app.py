import os
import secrets

from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.datastructures import ResponseHeader
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin

from home.controllers import ProjectController
from home.endpoints import home
from home.piccolo_app import APP_CONFIG
from litestar import Litestar, asgi, Response
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


cors_config = CORSConfig(
    allow_origins=[],
    allow_headers=[],
    allow_methods=[],
    allow_credentials=False,
)
csrf_config = CSRFConfig(
    secret=secrets.token_hex(16),
    cookie_secure=True,
    cookie_httponly=True,
)
rate_limit_config = RateLimitConfig(rate_limit=("second", 5), exclude=["/schema"])

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
    cors_config=cors_config,
    csrf_config=csrf_config,
    middleware=[rate_limit_config.middleware],
    response_headers=[
        ResponseHeader(
            name="x-frame-options",
            value="SAMEORIGIN",
            description="Security header",
        ),
        ResponseHeader(
            name="x-content-type-options",
            value="nosniff",
            description="Security header",
        ),
        ResponseHeader(
            name="referrer-policy",
            value="strict-origin",
            description="Security header",
        ),
        ResponseHeader(
            name="x-xss-protection",
            value="1; mode=block",
            description="Security header",
        ),
        ResponseHeader(
            name="permissions-policy",
            value="microphone=(); geolocation=(); fullscreen=();",
            description="Security header",
        ),
        ResponseHeader(
            name="content-security-policy",
            value="default-src 'none'; frame-ancestors 'none'; object-src 'none';"
            " base-uri 'none'; script-src 'nonce-{}' 'strict-dynamic'; style-src "
            "'nonce-{}' 'strict-dynamic'; require-trusted-types-for 'script'",
            description="Security header",
            documentation_only=True,
        ),
    ],
)
