import datetime
import typing as t
import uuid

from litestar import Controller, get, Request, post, patch
from litestar.exceptions import NotFoundException
from piccolo.apps.user.tables import BaseUser
from pydantic import BaseModel, Field

from home.middleware import EnsureAuth
from home.tables import Project, Scan


class User(BaseModel):
    id: int
    username: str
    email: str


class ProjectModelIn(BaseModel):
    created_at: datetime.datetime
    title: str
    description: str
    is_git_based: bool = Field(default=False)
    code_scanners: list[str] = Field(
        description="A list of Analysis Interface id's to use",
    )
    is_public: bool = Field(
        default=False,
        description="Should anyone be able to see and interact with this project?",
    )
    other_users: list[int] = Field(
        description="Other users who should have access to this. "
        "Defaults to user id since array foreign keys aren't allowed and i dont wanna do M2M",
    )


class ProjectModelOut(ProjectModelIn):
    id: uuid.UUID
    owner: User


class APIProjectController(Controller):
    path = "/api/projects"
    middleware = [EnsureAuth]

    @classmethod
    async def get_user_projects(cls, user: BaseUser) -> t.List[Project]:
        return await Project.add_ownership_where(
            Project.objects(Project.owner).order_by(Project.id, ascending=False),
            user,
        )

    @classmethod
    async def get_total_scans(cls, project: Project):
        return await Scan.count().where(
            Scan.project == project,  # type: ignore
        )

    @get(tags=["Projects API"])
    async def projects(self, request: Request) -> t.List[ProjectModelOut]:
        data: list[ProjectModelOut] = []
        for project in await self.get_user_projects(request.user):
            data.append(ProjectModelOut(**project.to_dict()))
        return data

    @post("/", tags=["Projects API"])
    async def create_project(
        self, request: Request, data: ProjectModelIn
    ) -> ProjectModelOut:
        project: Project = Project(**data.model_dump())
        project.owner = request.user
        await project.save()
        return ProjectModelOut(**project.to_dict())

    @patch("/{project_id:str}", tags=["Projects API"])
    async def update_project(
        self, request: Request, project_id: str, data: ProjectModelIn
    ) -> ProjectModelOut:
        project = Project.add_ownership_where(
            await Project.objects()
            .where(
                Project.id == project_id,  # type: ignore
            )
            .first(),
            request.user,
        )
        if not project:
            raise NotFoundException("Project does not exist")

        for key, value in data.model_dump().items():
            setattr(project, key, value)

        await project.save()
        return ProjectModelOut(**project.to_dict())
