import io
import logging
import os
import secrets
import shutil
import zipfile
from pathlib import Path
from typing import Annotated

from litestar import Controller, get, Request, MediaType, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Template, Redirect
from pydantic import BaseModel, ConfigDict

from home.controllers.api import APIProjectController, APIVulnerabilitiesController
from home.custom_request import HermesRequest
from home.middleware import EnsureAuth
from home.tables import Project, Vulnerability, Scan, Profile
from home.tables.vulnerability import VulnerabilityExploitability, VulnerabilityState
from home.util import get_csp, inject_spaces_into_string
from home.util.flash import alert
from home.configs import REGISTERED_INTERFACES, BASE_PROJECT_DIR
from home.saq import SAQ_QUEUE, SAQ_TIMEOUT

log = logging.getLogger(__name__)


class CreateProjectFormData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file: UploadFile | None


class VulnerabilityMetaData(BaseModel):
    exploitability: VulnerabilityExploitability
    state: VulnerabilityState


class ProjectMetaData(BaseModel):
    scan_number: int | None = None


class VulnerabilityNotesData(BaseModel):
    notes: str


# noinspection DuplicatedCode
class ProjectsController(Controller):
    path = "/projects"
    middleware = [EnsureAuth]

    @classmethod
    async def delete_project(cls, project: Project) -> None:
        code_path = Path(project.scanner_path)
        shutil.rmtree(code_path, ignore_errors=True)

        await Scan.delete().where(Scan.project == project)  # type: ignore
        await Vulnerability.delete().where(Vulnerability.project == project)  # type: ignore
        await project.delete().where(Project.id == project.uuid)  # type: ignore

    @classmethod
    async def get_project(
        cls, request: Request, project_id: str
    ) -> tuple[Project | None, Redirect | None]:
        project = await Project.add_ownership_where(
            Project.objects(Project.owner)
            .where(
                Project.id == project_id,  # type: ignore
            )
            .first(),
            request.user,
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
        vuln = await Vulnerability.add_ownership_where(
            Vulnerability.objects()
            .prefetch(Vulnerability.project)
            .where(Vulnerability.id == vulnerability_id)  # type: ignore
            .first(),
            request.user,
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
        cls, request: Request, current_vulnerability: Vulnerability
    ) -> str:
        """Fetch the 'next' vulnerability id to review"""
        # Given the use of UUID's this is so cooked hahaha
        vulns = await Vulnerability.add_ownership_where(
            Vulnerability.objects()
            .order_by(Vulnerability.id)
            .where(Vulnerability.scan == current_vulnerability.scan),  # type: ignore
            request.user,
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

        raise ValueError("Should never get here")

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
        request: HermesRequest,
        project_id: str,
        scan_number: int | None = None,
    ) -> Template | Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        scan: Scan | None = None
        scan_query = Scan.objects().where(
            Scan.project == project,  # type: ignore
        )
        if scan_number:
            scan = await scan_query.where(Scan.number == scan_number).first()

        if scan_number is None or scan is None:
            # Ensure we always have the latest
            scan = await scan_query.order_by(Scan.number, ascending=False).first()

        vulnerabilities: list[Vulnerability] = (
            await APIVulnerabilitiesController.get_scan_vulnerabilities(
                request.user, scan
            )
        )
        vulnerabilities = sorted(vulnerabilities, key=lambda v: v.title.title())
        total_scans = (await APIProjectController.get_total_scans(project)) + 1

        if request.is_small and len(project.title) > 20:
            # We need to split this into bits
            # which dont overflow the screen
            project_title = inject_spaces_into_string(project.title, 20)
        else:
            project_title = project.title

        csp, nonce = get_csp()
        return Template(
            "projects/overview.jinja",
            context={
                # scan is still scan: Scan | None
                # at this point and templates should
                # treat it as such where required
                "scan": scan,
                "is_small": request.is_small,
                "csp_nonce": nonce,
                "project": project,
                "active": "overview",
                "project_title": project_title,
                "total_scans": total_scans,
                "profile": await Profile.get_or_create(request.user),
                "projects": await APIProjectController.get_user_projects(request.user),
                "vulnerabilities": vulnerabilities,
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
        self, request: HermesRequest, project_id: str, vuln_id: str
    ) -> Template | Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        vuln, redirect = await self.get_vulnerability(request, project, vuln_id)
        if redirect:
            return redirect

        next_vuln_id = await self.get_next_vulnerability(request, vuln)

        if request.is_small and len(vuln.title) > 20:
            # We need to split this into bits
            # which dont overflow the screen
            vuln_title = inject_spaces_into_string(vuln.title, 20)
        else:
            vuln_title = vuln.title

        csp, nonce = get_csp()
        return Template(
            "projects/vulnerability.jinja",
            context={
                "next_vuln_id": next_vuln_id,
                "vuln": vuln,
                "vuln_title": vuln_title,
                "csp_nonce": nonce,
                "project": project,
                "active": "vulnerabilities",
                "is_small": request.is_small,
                "profile": await Profile.get_or_create(request.user),
                "projects": await APIProjectController.get_user_projects(request.user),
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )

    @post(
        path="/{project_id:str}/ui/metadata",
        include_in_schema=False,
    )
    async def project_metdata(
        self,
        project_id: str,
        data: Annotated[
            ProjectMetaData, Body(media_type=RequestEncodingType.MULTI_PART)
        ],
    ) -> Redirect:
        # TODO Handle pre-existing query parameters? Currently not required
        if data.scan_number:
            return Redirect(f"/projects/{project_id}?scan_number={data.scan_number}")

        # TODO Change to support exporting scans
        return Redirect(f"/projects/{project_id}")

    @post(
        path="/{project_id:str}/vulnerabilities/{vuln_id:str}/attributes",
        include_in_schema=False,
    )
    async def update_vuln_attributes(
        self,
        request: HermesRequest,
        project_id: str,
        vuln_id: str,
        data: Annotated[
            VulnerabilityMetaData, Body(media_type=RequestEncodingType.MULTI_PART)
        ],
    ) -> Template | Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        vuln, redirect = await self.get_vulnerability(request, project, vuln_id)
        if redirect:
            return redirect

        vuln.state = data.state
        vuln.exploitability = data.exploitability
        await vuln.save()
        return vuln.redirect_to()

    @post(
        path="/{project_id:str}/vulnerabilities/{vuln_id:str}/notes",
        include_in_schema=False,
    )
    async def update_vuln_notes(
        self,
        request: HermesRequest,
        project_id: str,
        vuln_id: str,
        data: Annotated[
            VulnerabilityNotesData, Body(media_type=RequestEncodingType.MULTI_PART)
        ],
    ) -> Template | Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        vuln, redirect = await self.get_vulnerability(request, project, vuln_id)
        if redirect:
            return redirect

        vuln.notes = data.notes
        await vuln.save()
        return vuln.redirect_to()

    @get(
        path="/{project_id:str}/settings",
        include_in_schema=False,
    )
    async def settings(
        self, request: HermesRequest, project_id: str
    ) -> Template | Redirect:
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
                "is_small": request.is_small,
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
    async def create_get(self, request: HermesRequest) -> Template:
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
                "is_small": request.is_small,
                "projects": await APIProjectController.get_user_projects(request.user),
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )

    @post(
        path="/create",
        include_in_schema=False,
        # 250 Megabytes max file size
        request_max_body_size=250 * 1_048_576,
    )
    async def create_project(
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

        project = Project(
            owner=request.user,
            title=title,
            description=description,
            is_git_based=git is not None,
            code_scanners=selected_interfaces,
            directory=project_dir,
        )
        await project.save()
        await project.refresh()

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

            alert(request, "Scheduled scanners to run. Results will be available soon")
            await SAQ_QUEUE.enqueue(
                "run_scanners",
                project_id=project.uuid,
                user_id=request.user.id,
                timeout=SAQ_TIMEOUT,
            )

        if git is not None:
            # Git clone it
            alert(
                request,
                "Started git clone, scanners will automatically run once complete",
            )
            await SAQ_QUEUE.enqueue(
                "git_clone",
                git=git,
                path_to_stuff=path_to_stuff,
                project_id=project.uuid,
                user_id=request.user.id,
                timeout=SAQ_TIMEOUT,
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

        await Scan.delete().where(
            Scan.project == project,  # type: ignore
        )
        await Vulnerability.delete().where(
            Vulnerability.project == project,  # type: ignore
        )
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
        return Redirect("/")

    @post(
        path="/{project_id:str}/settings/run_scanners",
        include_in_schema=False,
    )
    async def run_scanners(self, request: Request, project_id: str) -> Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        alert(request, "Scheduled scanners to run. Results will be available soon")
        await SAQ_QUEUE.enqueue(
            "run_scanners",
            project_id=project.uuid,
            user_id=request.user.id,
            timeout=SAQ_TIMEOUT,
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
        await SAQ_QUEUE.enqueue(
            "update_from_source",
            project_id=project.uuid,
            user_id=request.user.id,
            timeout=SAQ_TIMEOUT,
        )
        return project.redirect_to()

    @post(
        path="/{project_id:str}/settings/toggle_public_view",
        include_in_schema=False,
    )
    async def toggle_public_view(self, request: Request, project_id: str) -> Redirect:
        project, redirect = await self.get_project(request, project_id)
        if redirect:
            return redirect

        # Need to compare attributes while this is unresolved:
        # https://github.com/piccolo-orm/piccolo/issues/1075
        if project.owner.id != request.user.id:
            alert(
                request,
                "You must be the project owner to change project visibility.",
                level="error",
            )
            return project.redirect_to()

        project.is_public = not project.is_public
        await project.save()

        alert(
            request,
            f'Project is now {"public" if project.is_public else "no longer public"}',
        )
        return project.redirect_to()
