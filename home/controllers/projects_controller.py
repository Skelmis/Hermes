from litestar import Controller, get, Request, MediaType
from litestar.response import Template, Redirect

from home.controllers.api import APIProjectController
from home.middleware import EnsureAuth
from home.tables import Project
from home.util import get_csp
from home.util.flash import alert


# noinspection DuplicatedCode
class ProjectsController(Controller):
    path = "/projects"
    middleware = [EnsureAuth]

    @classmethod
    async def get_project(
        cls, request: Request, project_id: str
    ) -> tuple[Project | None, Redirect | None]:
        project = (
            await Project.objects()
            .where(Project.id == project_id)
            .where(Project.owner == request.user)  # type: ignore
            .first()
        )
        if not project:
            alert(
                request,
                f"Failed to find a project with id '{project_id}'",
                level="error",
            )
            return None, Redirect("/")

        return project, None

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
    async def overview(self, request: Request, project_id: str) -> Template | Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        csp, nonce = get_csp()
        return Template(
            "projects/overview.jinja",
            context={
                "csp_nonce": nonce,
                "project": project,
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )

    @get(
        path="/{project_id:str}/vulnerabilities",
        include_in_schema=False,
    )
    async def vulnerabilities(
        self, request: Request, project_id: str
    ) -> Template | Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        csp, nonce = get_csp()
        return Template(
            "projects/overview.jinja",
            context={
                "csp_nonce": nonce,
                "project": project,
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )

    @get(
        path="/{project_id:str}/settings",
        include_in_schema=False,
    )
    async def settings(self, request: Request, project_id: str) -> Template | Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect
        csp, nonce = get_csp()
        return Template(
            "projects/overview.jinja",
            context={
                "csp_nonce": nonce,
                "project": project,
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )
