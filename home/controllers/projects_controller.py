from litestar import Controller, get, Request, MediaType, post
from litestar.response import Template, Redirect

from home.controllers.api import APIProjectController, APIVulnerabilitiesController
from home.middleware import EnsureAuth
from home.tables import Project, Vulnerability
from home.util import get_csp
from home.util.flash import alert
from piccolo_conf import REGISTERED_INTERFACES


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
    async def projects(self, request: Request) -> Redirect:
        return Redirect("/")

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
                "active": "overview",
                "projects": await APIProjectController.get_user_projects(request.user),
                "vulnerabilities": await APIVulnerabilitiesController.get_project_vulnerabilities(
                    request.user, project
                ),
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
                "active": "vulnerabilities",
                "projects": await APIProjectController.get_user_projects(request.user),
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
            "projects/settings.jinja",
            context={
                "csp_nonce": nonce,
                "project": project,
                "active": "settings",
                "projects": await APIProjectController.get_user_projects(request.user),
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )

    @get(
        path="/create",
        include_in_schema=False,
    )
    async def create_get(self, request: Request) -> Template:
        csp, nonce = get_csp()
        return Template(
            "projects/create.jinja",
            context={
                "analysis_interfaces": [
                    f"{i.name} - {i.language}" for i in REGISTERED_INTERFACES
                ],
                "csp_nonce": nonce,
                "active": "settings",
                "projects": await APIProjectController.get_user_projects(request.user),
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )

    @post(
        path="/create",
        include_in_schema=False,
    )
    async def create_post(self, request: Request) -> Redirect:
        return Redirect("/projects")

    @post(
        path="/{project_id:str}/settings/delete/vulnerabilities",
        include_in_schema=False,
    )
    async def delete_vulns(self, request: Request, project_id: str) -> Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        await Vulnerability.delete().where(Vulnerability.project == project)
        alert(
            request,
            "Deleted all vulnerabilities associated with this project",
            level="success",
        )
        return Redirect(f"/projects/{project_id}/settings")

    @post(
        path="/{project_id:str}/settings/delete/project",
        include_in_schema=False,
    )
    async def delete_project(self, request: Request, project_id: str) -> Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        await Vulnerability.delete().where(Vulnerability.project == project)
        project_title = project.title
        await project.delete()
        alert(
            request,
            f"Deleted project '{project_title}' and associated vulnerabilities",
            level="success",
        )
        return Redirect(f"/")

    @post(
        path="/{project_id:str}/settings/run_scanners",
        include_in_schema=False,
    )
    async def run_scanners(self, request: Request, project_id: str) -> Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        bt = REGISTERED_INTERFACES[0]
        bandit = bt((await APIProjectController.get_user_projects(request.user))[0])
        await bandit.scan()
        alert(
            request,
            "Successfully ran scanners, results should appear soon.",
            level="success",
        )
        alert(
            request,
            "Note we cheated the lookup lol. It's hard coded to bandit rn",
        )
        return Redirect(f"/projects/{project_id}/settings")
