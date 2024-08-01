import typing as t

from litestar import Controller, get, Request, post, patch, delete
from litestar.exceptions import NotFoundException
from piccolo.utils.pydantic import create_pydantic_model

from home.tables import Project

ProjectModelIn: t.Any = create_pydantic_model(
    table=Project,
    model_name="ProjectModelIn",
)
ProjectModelOut: t.Any = create_pydantic_model(
    table=Project,
    include_default_columns=True,
    model_name="ProjectModelOut",
)


class ProjectController(Controller):
    path = "/projects"

    @get(tags=["Projects"])
    async def projects(self, request: Request) -> t.List[ProjectModelOut]:
        return Project.select().order_by(Project.id, ascending=False)

    @post("/projects", tags=["Projects"])
    async def create_project(self, data: ProjectModelIn) -> ProjectModelOut:
        project = Project(**data.dict())
        await project.save()
        return project.to_dict()

    @patch("/projects/{task_id:int}", tags=["Projects"])
    async def update_task(self, task_id: int, data: ProjectModelIn) -> ProjectModelOut:
        project = await Project.objects().get(Project.id == task_id)
        if not project:
            raise NotFoundException("Project does not exist")
        for key, value in data.dict().items():
            setattr(project, key, value)

        await project.save()
        return project.to_dict()

    @delete("/projects/{task_id:int}", tags=["Projects"])
    async def delete_task(self, task_id: int) -> None:
        project = await Project.objects().get(Project.id == task_id)
        if not project:
            raise NotFoundException("Task does not exist")
        await project.remove()
