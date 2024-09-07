from litestar import MediaType, Request, get
from litestar.response import Template

from home.controllers.api import APIProjectController
from home.filters.datetime import format_datetime
from home.middleware import EnsureAuth
from home.tables import Profile, Vulnerability
from home.util import get_csp
from piccolo_conf import REGISTERED_INTERFACES


@get(path="/", include_in_schema=False, middleware=[EnsureAuth])
async def home(request: Request) -> Template:
    csp, nonce = get_csp()
    profile = await Profile.get_or_create(request.user)
    projects = await APIProjectController.get_user_projects(request.user)
    raw_data = []
    for project in projects:
        scan = await project.get_last_scan()
        if scan:
            latest_scan = format_datetime(profile.localize_dt(scan.scanned_at))
            total_vulns = await Vulnerability.count().where(Vulnerability.scan == scan)
            total_resolved_vulns = await Vulnerability.count().where(
                Vulnerability.scan == scan
            )

        else:
            latest_scan = "No scan run"
            total_vulns = "N/A"
            total_resolved_vulns = "N/A"

        raw_data.append((project, latest_scan, total_vulns, total_resolved_vulns))

    data = list(sorted(raw_data, key=lambda e: e[1], reverse=True))

    return Template(
        template_name="home.jinja",
        context={
            "csp_nonce": nonce,
            "data_table": data,
            "projects": projects,
        },
        headers={"content-security-policy": csp},
        media_type=MediaType.HTML,
    )


@get(
    path="/settings",
    include_in_schema=False,
    middleware=[EnsureAuth],
)
async def settings(request: Request) -> Template:
    csp, nonce = get_csp()
    return Template(
        "settings.jinja",
        context={
            "csp_nonce": nonce,
            "projects": await APIProjectController.get_user_projects(request.user),
            "registered_interfaces": REGISTERED_INTERFACES.values(),
        },
        media_type=MediaType.HTML,
        headers={"content-security-policy": csp},
    )
