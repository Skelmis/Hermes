from litestar import Controller, get, Request, MediaType
from litestar.response import Template, Redirect

from home.controllers.api import APIProjectController
from home.middleware import EnsureAuth
from home.tables import Project
from home.util import get_csp
from home.util.flash import alert


class ProjectsController(Controller):
    path = "/projects"
    middleware = [EnsureAuth]

    @get(
        "/",
        include_in_schema=False,
    )
    async def projects(self, request: Request) -> Template:
        return Template(template_str="<p>Nothing to see here lol</P>")

    @get(
        path="/{project_id:str}",
        include_in_schema=False,
    )
    async def project_overview(
        self, request: Request, project_id: str
    ) -> Template | Redirect:
        csp, nonce = get_csp()
        project = await Project.objects().get(
            Project.id == project_id and Project.owner == request.user
        )
        if not project:
            alert(
                request,
                f"Failed to find a project with id '{project_id}'",
                level="error",
            )
            return Redirect("/")

        return Template(
            "project_overview.jinja",
            context={
                "csp_nonce": nonce,
                "project": project,
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )
