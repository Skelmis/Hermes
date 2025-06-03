from typing import Annotated

import arrow
import orjson
from litestar import Controller, get, Response, MediaType, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Template
from pydantic import BaseModel, ConfigDict

from home.controllers import ProjectsController
from home.controllers.api import APIProjectController
from home.custom_request import HermesRequest
from home.middleware import EnsureAuth
from home.tables import Scan, Archives, Profile
from home.util import orjson_util, get_csp
from home.util.flash import alert


class CreateProjectFormData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file: UploadFile


# noinspection DuplicatedCode
class ArchivesController(Controller):
    path = "/archives"
    middleware = [EnsureAuth]
    include_in_schema = False

    @get("/projects/{project_id:str}/scans/{scan_number:int}/export")
    async def export_scan_archive(
        self, request: HermesRequest, project_id: str, scan_number: int
    ) -> Redirect | Response:
        project, redirect = await ProjectsController.get_project(request, project_id)
        if redirect:
            return redirect

        scan: Scan | None = await Scan.objects().get(
            (Scan.project == project) & (Scan.number == scan_number)  # type: ignore
        )
        if scan is None:
            alert(
                request,
                f"Failed to find a scan numbered "
                f"{scan_number} on the project with id '{project_id}'",
                level="error",
            )
            return Redirect("/")

        data = await scan.export_as_json(request.user)
        return Response(
            orjson.dumps(data, option=orjson.OPT_INDENT_2, default=orjson_util.default),
            headers={"Content-Disposition": "attachment; filename=hermes_archive.json"},
            media_type=MediaType.JSON,
        )

    @get("")
    async def view_all_archives(self, request: HermesRequest) -> Template:
        archives: list[Archives] = await Archives.objects().where(
            Archives.owner == request.user  # type: ignore
        )
        archive_table = []
        for archive in archives:
            scan = orjson.loads(archive.scan)
            archive_table.append(
                [
                    scan["project"]["title"],
                    scan["project"]["description"],
                    scan["scanned_at"],
                    len(scan["vulnerabilities"]),
                    archive.uuid,
                ]
            )

        csp, nonce = get_csp()
        return Template(
            "archives/home.jinja",
            context={
                "csp_nonce": nonce,
                "archive_table": archive_table,
                "profile": await Profile.get_or_create(request.user),
                "projects": await APIProjectController.get_user_projects(request.user),
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )

    @get("/import")
    async def get_load_archive_page(self) -> Template:
        csp, nonce = get_csp()
        return Template(
            "archives/import.jinja",
            context={
                "csp_nonce": nonce,
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )

    @post(
        path="/import",
        # 250 Megabytes max file size
        request_max_body_size=250 * 1_048_576,
    )
    async def create_project(
        self,
        request: HermesRequest,
        data: Annotated[
            CreateProjectFormData, Body(media_type=RequestEncodingType.MULTI_PART)
        ],
    ) -> Redirect:
        data = orjson.loads(await data.file.read())
        archives = Archives(
            owner=request.user,
            archive_created_at=arrow.get(data["archive_created_at"]).datetime,
            archive_creator=data["archive_creator"],
            scan=data["scan"],
        )
        await archives.save()
        await archives.refresh()
        return archives.redirect_to()

    @get("/{archive_id:str}")
    async def view_archive(
        self, request: HermesRequest, archive_id: str
    ) -> Template | Redirect:
        archive: Archives | None = await Archives.objects().get(
            (Archives.owner == request.user) & (Archives.id == archive_id)  # type: ignore
        )
        if archive is None:
            alert(
                request, "Looks like that archive doesn't exist for you.", level="error"
            )
            return Redirect("/archives")

        scan = orjson.loads(archive.scan)
        vulnerabilities = sorted(
            scan["vulnerabilities"], key=lambda v: v["title"].title()
        )

        csp, nonce = get_csp()
        return Template(
            "archives/overview.jinja",
            context={
                "csp_nonce": nonce,
                "archive_uuid": archive.uuid,
                "project_title": scan["project"]["title"],
                "project": scan["project"],
                "scan": scan,
                "active": "overview",
                "vulnerabilities": vulnerabilities,
                "profile": await Profile.get_or_create(request.user),
                "projects": await APIProjectController.get_user_projects(request.user),
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )

    @get(
        path="/{archive_id:str}/vulnerabilities",
    )
    async def vulnerabilities_without_vuln(
        self,
        request: HermesRequest,
        archive_id: str,
    ) -> Redirect:
        alert(request, "Please provide the vulnerability to review and try again")
        return Redirect(f"/archives/{archive_id}")

    @get("/{archive_id:str}/vulnerabilities/{vulnerability_id:int}")
    async def view_archive_vuln(
        self,
        request: HermesRequest,
        archive_id: str,
        vulnerability_id: int,
    ) -> Template | Redirect:
        archive: Archives | None = await Archives.objects().get(
            (Archives.owner == request.user) & (Archives.id == archive_id)  # type: ignore
        )
        if archive is None:
            alert(request, "Looks like that archive doesn't exist.", level="error")
            return Redirect("/archives")

        scan = orjson.loads(archive.scan)
        try:
            vuln = scan["vulnerabilities"][vulnerability_id]
        except IndexError:
            alert(request, "Looks like that vulnerability doesnt exist.", level="error")
            return Redirect(f"/archives/{archive_id}")

        next_vuln_id = (
            0
            if vulnerability_id == len(scan["vulnerabilities"]) - 1
            else vulnerability_id + 1
        )
        csp, nonce = get_csp()
        return Template(
            "archives/vulnerability.jinja",
            context={
                "csp_nonce": nonce,
                "archive_uuid": archive.uuid,
                "project_title": scan["project"]["title"],
                "project": scan["project"],
                "scan": scan,
                "vuln": vuln,
                "active": "vulnerabilities",
                "next_vuln_id": next_vuln_id,
                "profile": await Profile.get_or_create(request.user),
                "projects": await APIProjectController.get_user_projects(request.user),
            },
            media_type=MediaType.HTML,
            status_code=200,
            headers={"content-security-policy": csp},
        )

    @post(
        path="/{archive_id:str}/settings/delete",
        include_in_schema=False,
    )
    async def delete_archive_route(
        self, request: HermesRequest, archive_id: str
    ) -> Redirect:
        archive: Archives | None = await Archives.objects().get(
            (Archives.owner == request.user) & (Archives.id == archive_id)  # type: ignore
        )
        if archive is None:
            alert(request, "Looks like that archive doesn't exist.", level="error")
            return Redirect("/archives")

        scan = orjson.loads(archive.scan)
        archive_title = scan["project"]["title"]
        await Archives.delete().where(
            (Archives.owner == request.user) & (Archives.id == archive_id)  # type: ignore
        )
        alert(
            request,
            f"Deleted archive '{archive_title}'",
            level="success",
        )
        return Redirect("/archives")

    @post(
        path="/{archive_id:str}/settings/export",
        include_in_schema=False,
    )
    async def archive_export(self, request: HermesRequest, archive_id: str) -> Response:
        """Re-export a scan"""
        archive: Archives | None = await Archives.objects().get(
            (Archives.owner == request.user) & (Archives.id == archive_id)  # type: ignore
        )
        if archive is None:
            alert(request, "Looks like that archive doesn't exist.", level="error")
            return Redirect("/archives")

        data = {
            "scan": archive.scan,
            "archive_created_at": archive.created_at,
            "archive_creator": archive.archive_creator,
        }
        return Response(
            orjson.dumps(data, option=orjson.OPT_INDENT_2, default=orjson_util.default),
            headers={"Content-Disposition": "attachment; filename=hermes_archive.json"},
            media_type=MediaType.JSON,
        )
