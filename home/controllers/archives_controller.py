import orjson
from litestar import Controller, get, Response, MediaType
from litestar.response import Redirect, Template

from home.controllers import ProjectsController
from home.custom_request import HermesRequest
from home.middleware import EnsureAuth
from home.tables import Scan
from home.util import orjson_util, get_csp
from home.util.flash import alert


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
            (Scan.project == project) & (Scan.number == scan_number)
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
