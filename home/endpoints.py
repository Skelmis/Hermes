from litestar import MediaType, Request, Response, get
from litestar.response import Template

from home.controllers import ProjectController
from home.middleware import EnsureAuth
from home.tables import Project
from home.util import get_csp
from home.util.flash import alert
from piccolo_conf import REGISTERED_INTERFACES


@get(path="/", include_in_schema=False, sync_to_thread=False, middleware=[EnsureAuth])
async def home(request: Request) -> Template:
    csp, nonce = get_csp()
    alert(request, "Oh no! I've been flashed!", level="info")
    alert(request, "Oh no! I've been flashed!", level="success")
    alert(request, "Oh no! I've been flashed!", level="warning")
    alert(request, "Oh no! I've been flashed!", level="error")
    return Template(
        template_name="home.jinja",
        context={
            "csp_nonce": nonce,
            "projects": await ProjectController.get_user_projects(request.user),
        },
        headers={"content-security-policy": csp},
        media_type=MediaType.HTML,
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


@get(
    path="/project/{project_id:str}",
    include_in_schema=False,
    sync_to_thread=False,
    middleware=[EnsureAuth],
)
async def project_overview(request: Request, project_id: str) -> Response:
    csp, nonce = get_csp()
    template = ENVIRONMENT.get_template("project_overview.jinja")
    project = await Project.objects().where(
        Project.id == project_id and Project.owner == request.user
    )
    if not project:
        pass

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
