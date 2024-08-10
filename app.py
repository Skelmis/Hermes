import os
import secrets
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import jinja2
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from litestar import Litestar, asgi
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.datastructures import ResponseHeader
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.plugins.flash import FlashPlugin, FlashConfig
from litestar.static_files import StaticFilesConfig
from litestar.template import TemplateConfig
from litestar.types import Receive, Scope, Send
from piccolo.engine import engine_finder
from piccolo_admin.endpoints import create_admin

from home.controllers import (
    LoginController,
    LogoutController,
    SignUpController,
    ProjectsController,
)
from home.controllers.api import APIProjectController
from home.endpoints import home, settings
from home.exception_handlers import redirect_for_auth, RedirectForAuth
from home.filters.datetime import format_datetime
from home.piccolo_app import APP_CONFIG
from home.tasks import keep_projects_updated
from piccolo_conf import ASYNC_SCHEDULER

load_dotenv()
IS_PRODUCTION = not bool(os.environ.get("DEBUG", False))


# mounting Piccolo Admin
@asgi("/admin/", is_mount=True)
async def admin(scope: "Scope", receive: "Receive", send: "Send") -> None:
    await create_admin(
        tables=APP_CONFIG.table_classes,
        production=IS_PRODUCTION,
        allowed_hosts=["hermes.skelmis.co.nz"],
        sidebar_links={"Site root": "/"},
        site_name="Hermes Admin",
        auto_include_related=True,
    )(scope, receive, send)


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


@asynccontextmanager
async def handle_scheduler_lifecycle(_: Litestar) -> AsyncGenerator[None, None]:
    async with ASYNC_SCHEDULER:
        if IS_PRODUCTION:
            await ASYNC_SCHEDULER.add_schedule(
                keep_projects_updated, IntervalTrigger(hours=1)
            )
        else:
            await ASYNC_SCHEDULER.add_schedule(
                keep_projects_updated, IntervalTrigger(seconds=15)
            )
        await ASYNC_SCHEDULER.start_in_background()

        try:
            yield
        finally:
            # Do this to ensure we exit
            pass


cors_config = CORSConfig(
    allow_origins=[],
    allow_headers=[],
    allow_methods=[],
    allow_credentials=False,
)
CSRF_TOKEN = os.environ.get("CSRF_TOKEN", secrets.token_hex(32))
csrf_config = CSRFConfig(
    secret=CSRF_TOKEN,
    # Aptly named so it doesnt clash
    # with piccolo csrftoken' cookies
    cookie_name="csrf_token",
    cookie_secure=True,
    cookie_httponly=True,
    # Exclude routes Piccolo handles itself
    # and our api routes
    exclude=[
        "/admin",
        "/login",
        "/logout",
        "/api/v1",
    ],
)
rate_limit_config = RateLimitConfig(
    rate_limit=("second", 5), exclude=["/docs", "/admin"]
)
ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        searchpath=os.path.join(os.path.dirname(__file__), "home", "templates")
    ),
    autoescape=True,
)
ENVIRONMENT.filters["fmt"] = format_datetime
template_config = TemplateConfig(
    directory="home/templates", engine=JinjaTemplateEngine.from_environment(ENVIRONMENT)
)
flash_plugin = FlashPlugin(config=FlashConfig(template_config=template_config))
session_config = CookieBackendConfig(secret=os.urandom(16))
app = Litestar(
    route_handlers=[
        admin,
        home,
        settings,
        APIProjectController,
        LoginController,
        LogoutController,
        SignUpController,
        ProjectsController,
    ],
    template_config=template_config,
    static_files_config=[
        StaticFilesConfig(directories=["static"], path="/static/"),
    ],
    lifespan=[handle_scheduler_lifecycle],
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
    middleware=[rate_limit_config.middleware, session_config.middleware],
    plugins=[flash_plugin],
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
    exception_handlers={RedirectForAuth: redirect_for_auth},
)
