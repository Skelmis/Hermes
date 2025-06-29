import typing as t

from litestar import Controller
from piccolo.apps.user.tables import BaseUser
from piccolo.utils.pydantic import create_pydantic_model

from home.middleware import EnsureAuth
from home.tables import Vulnerability, Project, Scan

VulnModelIn: t.Any = create_pydantic_model(
    table=Vulnerability,
    exclude_columns=(Vulnerability.id,),
    model_name="VulnModelIn",
)
VulnModelOut: t.Any = create_pydantic_model(
    table=Vulnerability,
    include_default_columns=True,
    model_name="VulnModelOut",
    nested=True,
)


class APIVulnerabilitiesController(Controller):
    path = "/api/projects"
    middleware = [EnsureAuth]

    @classmethod
    async def get_project_vulnerabilities(
        cls, user: BaseUser, project: Project
    ) -> t.List[Vulnerability]:
        return await Vulnerability.add_ownership_where(
            Vulnerability.objects()
            .where(Vulnerability.scan.project == project)  # type: ignore
            .order_by(Vulnerability.title, ascending=False),
            user,
        )

    @classmethod
    async def get_scan_vulnerabilities(
        cls, user: BaseUser, scan: Scan
    ) -> t.List[Vulnerability]:
        return await Vulnerability.add_ownership_where(
            Vulnerability.objects()
            .where(Vulnerability.scan == scan)  # type: ignore
            .order_by(Vulnerability.title, ascending=False),
            user,
        )
