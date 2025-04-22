import orjson
from litestar import Controller, get, Response
from litestar.response import Redirect

from home.controllers import ProjectsController
from home.custom_request import HermesRequest
from home.middleware import EnsureAuth
from home.tables import Scan
from home.util import orjson_util
from home.util.flash import alert


# noinspection DuplicatedCode
class ArchivesController(Controller):
    path = "/archives"
    middleware = [EnsureAuth]

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
            headers={
                "Content-Disposition": "attachment; filename='hermes_archive.json'"
            },
        )
