import os

import jinja2
from litestar import MediaType, Request, Response, get

from home.middleware import EnsureAuth
from home.util import get_csp
from home.controllers import ProjectController
from piccolo_conf import REGISTERED_INTERFACES

ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        searchpath=os.path.join(os.path.dirname(__file__), "templates")
    ),
    autoescape=True,
)


@get(path="/", include_in_schema=False, sync_to_thread=False, middleware=[EnsureAuth])
async def home(request: Request) -> Response:
    csp, nonce = get_csp()
    template = ENVIRONMENT.get_template("home.jinja")
    content = template.render(
        csp_nonce=nonce,
        projects=await ProjectController.get_user_projects(request.user),
    )
    return Response(
        content,
        media_type=MediaType.HTML,
        status_code=200,
        headers={"content-security-policy": csp},
    )


@get(
    path="/settings",
    include_in_schema=False,
    sync_to_thread=False,
    middleware=[EnsureAuth],
)
async def settings(request: Request) -> Response:
    csp, nonce = get_csp()
    template = ENVIRONMENT.get_template("settings.jinja")
    content = template.render(
        csp_nonce=nonce,
        projects=await ProjectController.get_user_projects(request.user),
        registered_interfaces=REGISTERED_INTERFACES,
    )

    return Response(
        content,
        media_type=MediaType.HTML,
        status_code=200,
        headers={"content-security-policy": csp},
    )
