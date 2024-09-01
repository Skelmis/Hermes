import io
import logging
import os
import secrets
import shutil
import subprocess
import zipfile
from datetime import timedelta, datetime
from functools import partial
from pathlib import Path
from typing import Annotated

import commons
from apscheduler.triggers.date import DateTrigger
from litestar import Controller, get, Request, MediaType, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Template, Redirect
from pydantic import BaseModel, ConfigDict

from home.controllers.api import APIProjectController, APIVulnerabilitiesController
from home.middleware import EnsureAuth
from home.tables import Project, Vulnerability, Scan, Profile
from home.util import get_csp
from home.util.flash import alert
from piccolo_conf import REGISTERED_INTERFACES, BASE_PROJECT_DIR, ASYNC_SCHEDULER

log = logging.getLogger(__name__)


class CreateProjectFormData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file: UploadFile | None


# noinspection DuplicatedCode
class ProjectsController(Controller):
    path = "/projects"
    middleware = [EnsureAuth]

    @classmethod
    async def delete_project(cls, project: Project) -> None:
        code_path = Path(project.scanner_path)
        shutil.rmtree(code_path, ignore_errors=True)

        await Scan.delete().where(Scan.project == project)
        await Vulnerability.delete().where(Vulnerability.project == project)
        await project.delete().where(Project.id == project.uuid)

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

    @classmethod
    async def get_vulnerability(
        cls, request: Request, project: Project, vulnerability_id: str
    ) -> tuple[Vulnerability | None, Redirect | None]:
        vuln = (
            await Vulnerability.objects()
            .where(Vulnerability.id == vulnerability_id)
            .where(Vulnerability.project.owner == request.user)  # type: ignore
            .first()
        )
        if not vuln:
            alert(
                request,
                f"Failed to find a vulnerability with id '{vulnerability_id}'",
                level="error",
            )
            return None, Redirect(f"/projects/{project.uuid}")

        return vuln, None

    @classmethod
    async def get_next_vulnerability(
        cls, request: Request, project: Project, current_vulnerability: Vulnerability
    ) -> str:
        """Fetch the 'next' vulnerability id to review"""
        # Given the use of UUID's this is so cooked hahaha
        vulns = (
            await Vulnerability.objects()
            .order_by(Vulnerability.id)
            .where(Vulnerability.scan == current_vulnerability.scan)  # type: ignore
            .where(Vulnerability.project.owner == request.user)  # type: ignore
        )
        if not vulns:
            # Fuck knows what went wrong
            return current_vulnerability.id

        for i, vuln in enumerate(vulns):
            if vuln.id == current_vulnerability.id:
                if len(vulns) - 1 == i:
                    # Its last vuln so loop around
                    return vulns[0].id
                else:
                    return vulns[i + 1].id

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
    async def overview(
        self,
        request: Request,
        project_id: str,
        scan_number: int = None,
    ) -> Template | Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        scan: Scan | None = None
        scan_query = Scan.objects().where(Scan.project == project)
        if scan_number:
            scan = await scan_query.where(Scan.id == scan_number).first()

        if scan_number is None or scan is None:
            # Ensure we always have the latest
            scan = await scan_query.order_by(Scan.number, ascending=False).first()

        csp, nonce = get_csp()
        return Template(
            "projects/overview.jinja",
            context={
                "scan": scan,
                "csp_nonce": nonce,
                "project": project,
                "active": "overview",
                "profile": await Profile.get_or_create(request.user),
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
    async def vulnerabilities_without_vuln(
        self,
        request: Request,
        project_id: str,
    ) -> Redirect:
        alert(request, "Please provide the vulnerability to review and try again")
        return Redirect(f"/projects/{project_id}")

    @get(
        path="/{project_id:str}/vulnerabilities/{vuln_id:str}",
        include_in_schema=False,
    )
    async def vulnerabilities_view(
        self, request: Request, project_id: str, vuln_id: str
    ) -> Template | Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        vuln, redirect = await self.get_vulnerability(request, project, vuln_id)
        if redirect:
            return redirect

        next_vuln_id = await self.get_next_vulnerability(request, project, vuln)

        csp, nonce = get_csp()
        return Template(
            "projects/vulnerability.jinja",
            context={
                "next_vuln_id": next_vuln_id,
                "vuln": vuln,
                "csp_nonce": nonce,
                "project": project,
                "active": "vulnerabilities",
                "profile": await Profile.get_or_create(request.user),
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
                    (f"{i.name} - {i.language}", _id)
                    for _id, i in REGISTERED_INTERFACES.items()
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
    async def create_post(
        self,
        request: Request,
        data: Annotated[
            CreateProjectFormData, Body(media_type=RequestEncodingType.MULTI_PART)
        ],
    ) -> Redirect:
        has_errors = False
        file = data.file
        form_data = await request.form()
        title: str | None = form_data.get("title", None)
        description: str = form_data.get("description") or ""
        git: str | None = form_data.get("git", None)
        selected_interfaces = []
        for pi in REGISTERED_INTERFACES.keys():
            present = form_data.get(pi, None)
            if present == "on":
                selected_interfaces.append(pi)

        # Minimum form validation time
        if title is None:
            alert(request, "New projects require a title", level="error")
            has_errors = True

        if git is None and file is None:
            alert(
                request,
                "A git URL or source code is required for new projects",
                level="error",
            )
            has_errors = True

        if git is not None and file is not None:
            alert(
                request,
                "Please only provide source code or git, not both",
                level="error",
            )
            has_errors = True

        if not selected_interfaces:
            alert(
                request,
                "Please select at-least one interface to do code scanning with",
                level="error",
            )
            has_errors = True

        if has_errors:
            return Redirect("/projects/create")

        project_dir = secrets.token_hex(8)
        path_to_stuff = BASE_PROJECT_DIR / project_dir
        path_to_stuff.mkdir()
        path_to_stuff = str(path_to_stuff)

        if file is not None:
            # Write to disk time
            content = await file.read()
            with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
                for member in zf.infolist():
                    # TODO Test a path traversal on this
                    file_path = os.path.realpath(
                        os.path.join(path_to_stuff, member.filename)
                    )
                    if file_path.startswith(os.path.realpath(path_to_stuff)):
                        zf.extract(member, path_to_stuff)

        if git is not None:
            # Git clone it
            cmd = ["git", "clone", "--recursive", git, path_to_stuff]
            try:
                output = subprocess.check_output(cmd)
            except Exception as e:
                alert(request, "Something went wrong, check the logs", level="error")
                log.error(
                    "Git cloning died with error\n%s", commons.exception_as_string(e)
                )
                return Redirect("/projects/create")

        project = Project(
            owner=request.user,
            title=title,
            description=description,
            is_git_based=git is not None,
            code_scanners=selected_interfaces,
            directory=project_dir,
        )
        await project.save()
        alert(request, "Scheduled scanners to run. Results will be available soon")
        await ASYNC_SCHEDULER.add_schedule(
            partial(project.run_scanners, request),
            DateTrigger(datetime.now() + timedelta(seconds=5)),
        )

        return project.redirect_to()

    @post(
        path="/{project_id:str}/settings/delete/vulnerabilities",
        include_in_schema=False,
    )
    async def delete_vulns(self, request: Request, project_id: str) -> Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        await Scan.delete().where(Scan.project == project)
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
    async def delete_project_route(self, request: Request, project_id: str) -> Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        project_title = project.title
        await self.delete_project(project)
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

        alert(request, "Scheduled scanners to run. Results will be available soon")
        await ASYNC_SCHEDULER.add_schedule(
            partial(project.run_scanners, request),
            DateTrigger(datetime.now() + timedelta(seconds=5)),
        )

        return project.redirect_to()

    @post(
        path="/{project_id:str}/settings/pull_code",
        include_in_schema=False,
    )
    async def pull_latest_code(self, request: Request, project_id: str) -> Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        alert(request, "Scheduled the pull, it'll be ready momentarily")
        await ASYNC_SCHEDULER.add_schedule(
            partial(project.update_from_source, request),
            DateTrigger(datetime.now() + timedelta(seconds=5)),
        )
        return project.redirect_to()
