import typing as t

from litestar import Controller, get, Request, post, patch, delete
from litestar.exceptions import NotFoundException
from piccolo.apps.user.tables import BaseUser
from piccolo.utils.pydantic import create_pydantic_model

from home.middleware import EnsureAuth
from home.tables import Project

ProjectModelIn: t.Any = create_pydantic_model(
    table=Project,
    exclude_columns=(Project.id, Project.owner),
    model_name="ProjectModelIn",
)
ProjectModelOut: t.Any = create_pydantic_model(
    table=Project,
    include_default_columns=True,
    model_name="ProjectModelOut",
    nested=True,
)


class APIProjectController(Controller):
    path = "/api/projects"
    middleware = [EnsureAuth]

    @classmethod
    async def get_user_projects(cls, user: BaseUser) -> t.List[Project]:
        return await (
            Project.objects()
            .where(Project.owner == user)
            .order_by(Project.id, ascending=False)
        )

    @get(tags=["Projects API"])
    async def projects(self, request: Request) -> t.List[ProjectModelOut]:
        return await self.get_user_projects(request.user)

    @post("/", tags=["Projects API"])
    async def create_project(
        self, request: Request, data: ProjectModelIn
    ) -> ProjectModelOut:
        project = Project(**data.dict())
        project.owner = request.user
        await project.save()
        return project.to_dict()

    @patch("/{project_id:str}", tags=["Projects API"])
    async def update_project(
        self, request: Request, project_id: str, data: ProjectModelIn
    ) -> ProjectModelOut:
        project = (
            await Project.objects()
            .where(Project.id == project_id)
            .where(Project.owner == request.user)  # type: ignore
            .first()
        )
        if not project:
            raise NotFoundException("Project does not exist")

        for key, value in data.dict().items():
            setattr(project, key, value)

        await project.save()
        return project.to_dict()

    @delete("/{project_id:str}", tags=["Projects API"])
    async def delete_project(self, request: Request, project_id: str) -> None:
        project: Project | None = (
            await Project.objects()
            .where(Project.id == project_id)
            .where(Project.owner == request.user)  # type: ignore
            .first()
        )
        if not project:
            raise NotFoundException("Project does not exist")

        await project.remove()
