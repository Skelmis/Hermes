from __future__ import annotations

from typing import TYPE_CHECKING

import orjson
from piccolo.apps.user.tables import BaseUser
from piccolo.columns import (
    Serial,
    ForeignKey,
    LazyTableReference,
    JSONB,
    JSON,
    Or,
    Where,
)
from piccolo.columns.operators import ILike
from piccolo.table import Table
from pydantic import BaseModel


class AnalysisInterfaceFilter(BaseModel):
    id: str
    ticked: bool
    name: str


class StateFilter(BaseModel):
    new: bool
    triage: bool
    resolved: bool


class ExploitabilityFilter(BaseModel):
    unknown: bool
    not_exploitable: bool
    exploitable: bool


class Configuration(BaseModel):
    search: str | None
    excluded_file_path: str | None
    analysis_interfaces: list[AnalysisInterfaceFilter]
    state: StateFilter
    exploitability: ExploitabilityFilter


DEFAULT = Configuration(
    search=None,
    excluded_file_path=None,
    analysis_interfaces=[],
    state=StateFilter(new=True, triage=True, resolved=True),
    exploitability=ExploitabilityFilter(
        unknown=True, not_exploitable=True, exploitable=True
    ),
)


class ProjectFilters(Table):
    if TYPE_CHECKING:
        id: Serial

    user = ForeignKey(
        BaseUser,
        index=True,
        help_text="Who owns this project",
        null=False,
        required=True,
    )
    project = ForeignKey(
        LazyTableReference("Project", module_path="home.tables"),
        index=True,
        help_text="What project is this for?",
        null=False,
        required=True,
    )
    configuration = JSON()

    @classmethod
    async def get_object(cls, *, user, project) -> ProjectFilters:
        obj = (
            await cls.objects()
            .where(cls.user == user)
            .where(cls.project == project)
            .first()
        )
        if obj:
            return obj

        obj = cls(user=user, project=project, configuration=DEFAULT.model_dump_json())
        conf = obj.configuration_model
        from home.configs import REGISTERED_INTERFACES

        for pi, name in REGISTERED_INTERFACES.items():
            if pi in project.code_scanners:
                conf.analysis_interfaces.append(
                    AnalysisInterfaceFilter(id=pi, name=name.name, ticked=True)
                )
        obj.configuration_model = conf
        await obj.save()
        return obj

    @property
    def configuration_model(self) -> Configuration:
        return Configuration(**orjson.loads(self.configuration))

    @configuration_model.setter
    def configuration_model(self, value: Configuration):
        self.configuration = value.model_dump_json()

    def add_to_query(self, query):
        from home.tables import Vulnerability
        from home.tables.vulnerability import (
            VulnerabilityState,
            VulnerabilityExploitability,
        )

        filter_configuration = self.configuration_model
        if filter_configuration.search:
            query = query.where(
                Or(
                    Where(
                        Vulnerability.title,
                        f"%{filter_configuration.search}%",
                        operator=ILike,
                    ),
                    Or(
                        Where(
                            Vulnerability.description,
                            f"%{filter_configuration.search}%",
                            operator=ILike,
                        ),
                        Or(
                            Where(
                                Vulnerability.notes,
                                f"%{filter_configuration.search}%",
                                operator=ILike,
                            ),
                            Or(
                                Where(
                                    Vulnerability.code_file,
                                    f"%{filter_configuration.search}%",
                                    operator=ILike,
                                ),
                                Where(
                                    Vulnerability.code_context,
                                    f"%{filter_configuration.search}%",
                                    operator=ILike,
                                ),
                            ),
                        ),
                    ),
                )
            )

        if filter_configuration.excluded_file_path:
            query = query.where(
                Vulnerability.code_file.not_like(
                    f"%{filter_configuration.excluded_file_path}%"
                )
            )

        for ai in filter_configuration.analysis_interfaces:
            if ai.ticked:
                continue

            query = query.where(Vulnerability.found_by != ai.id)

        if not filter_configuration.state.new:
            query = query.where(Vulnerability.state != VulnerabilityState.NEW)
        if not filter_configuration.state.triage:
            query = query.where(Vulnerability.state != VulnerabilityState.UNDER_TRIAGE)
        if not filter_configuration.state.resolved:
            query = query.where(Vulnerability.state != VulnerabilityState.RESOLVED)

        if not filter_configuration.exploitability.unknown:
            query = query.where(
                Vulnerability.exploitability != VulnerabilityExploitability.UNKNOWN
            )
        if not filter_configuration.exploitability.not_exploitable:
            query = query.where(
                Vulnerability.exploitability
                != VulnerabilityExploitability.NOT_EXPLOITABLE
            )
        if not filter_configuration.exploitability.exploitable:
            query = query.where(
                Vulnerability.exploitability != VulnerabilityExploitability.EXPLOITABLE
            )

        return query
