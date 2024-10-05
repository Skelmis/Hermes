import os
import secrets

import jinja2
from commons import value_to_bool
from dotenv import load_dotenv
from litestar import Litestar, asgi
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.datastructures import ResponseHeader
from litestar.exceptions import NotFoundException, ImproperlyConfiguredException
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.plugins.flash import FlashPlugin, FlashConfig
from litestar.static_files import StaticFilesConfig
from litestar.template import TemplateConfig
from litestar.types import Receive, Scope, Send
from piccolo.apps.user.tables import BaseUser
from piccolo.engine import engine_finder
from piccolo_admin.endpoints import create_admin, TableConfig, OrderBy

from home.controllers import (
    LoginController,
    LogoutController,
    SignUpController,
    ProjectsController,
    PasswordController,
)
from home.controllers.api import APIProjectController
from home.custom_request import HermesRequest
from home.endpoints import home, settings
from home.exception_handlers import (
    redirect_for_auth,
    RedirectForAuth,
    handle_404,
    handle_500,
)
from home.filters import pretty_json
from home.filters.datetime import format_datetime
from home.tables import (
    Profile,
    Notification,
    Project,
    ProjectAutomation,
    Scan,
    Vulnerability,
)

load_dotenv()
IS_PRODUCTION = not value_to_bool(os.environ.get("DEBUG"))


# mounting Piccolo Admin
@asgi("/admin/", is_mount=True)
async def admin(scope: "Scope", receive: "Receive", send: "Send") -> None:
    user_tc = TableConfig(BaseUser, menu_group="User Management")
    profile_tc = TableConfig(Profile, menu_group="User Management")
    notification_tc = TableConfig(
        Notification,
        menu_group="User Management",
        order_by=[
            OrderBy(Notification.target),
            OrderBy(Notification.created_at, ascending=False),
        ],
    )

    project_tc = TableConfig(
        Project,
        menu_group="Project Management",
        order_by=[OrderBy(Project.owner), OrderBy(Project.created_at, ascending=False)],
        visible_columns=[
            Project.id,
            Project.owner,
            Project.title,
            Project.created_at,
            Project.is_git_based,
            Project.code_scanners,
        ],
    )
    automation_tc = TableConfig(
        ProjectAutomation,
        menu_group="Project Management",
        order_by=[
            OrderBy(ProjectAutomation.project),
        ],
    )
    scan_tc = TableConfig(
        Scan,
        menu_group="Project Management",
        order_by=[
            OrderBy(Scan.created_at, ascending=False),
            OrderBy(Scan.number, ascending=False),
        ],
        visible_columns=[Scan.id, Scan.project, Scan.number, Scan.created_at],
    )
    vulnerability_tc = TableConfig(
        Vulnerability,
        menu_group="Project Management",
        order_by=[OrderBy(Vulnerability.created_at, ascending=False)],
        visible_columns=[
            Vulnerability.id,
            Vulnerability.title,
            Vulnerability.state,
            Vulnerability.exploitability,
            Vulnerability.found_by,
            Vulnerability.created_at,
        ],
    )

    await create_admin(
        tables=[
            user_tc,
            profile_tc,
            notification_tc,
            project_tc,
            automation_tc,
            scan_tc,
            vulnerability_tc,
        ],
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
    # with piccolo 'csrftoken' cookies
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
ENVIRONMENT.filters["pretty_json"] = pretty_json
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
        PasswordController,
    ],
    template_config=template_config,
    static_files_config=[
        StaticFilesConfig(directories=["static"], path="/static/"),
    ],
    on_startup=[open_database_connection_pool],
    on_shutdown=[close_database_connection_pool],
    debug=not IS_PRODUCTION,
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
    exception_handlers={
        RedirectForAuth: redirect_for_auth,
        NotFoundException: handle_404,
        ImproperlyConfiguredException: handle_500,
    },
    request_class=HermesRequest,
)
