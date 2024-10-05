import asyncio
import datetime
import logging

import anyio
import commons
from piccolo.apps.user.tables import BaseUser
from saq import CronJob

from home.tables import Project, Notification
from piccolo_conf import SAQ_QUEUE

log = logging.getLogger(__name__)


async def git_clone(_, *, git, path_to_stuff, project_id: str, user_id: str):
    project: Project = await Project.objects().get(Project.id == project_id)
    user: BaseUser = await BaseUser.objects().get(BaseUser.id == user_id)
    cmd = ["git", "clone", "--recursive", git, path_to_stuff]
    try:
        await anyio.run_process(cmd)
    except Exception as e:
        await Notification.create_alert(
            user,
            "Something went wrong, check the logs",
            level="error",
        )
        log.error("Git cloning died with error\n%s", commons.exception_as_string(e))
    else:
        await SAQ_QUEUE.enqueue(
            "run_scanners",
            project_id=project.uuid,
            user_id=user.id,
        )


async def run_scanners(_, *, project_id: str, user_id: str):
    project: Project = await Project.objects().get(Project.id == project_id)
    user: BaseUser = await BaseUser.objects().get(BaseUser.id == user_id)
    await project.run_scanners(user)


async def update_from_source(_, *, project_id: str, user_id: str):
    project: Project = await Project.objects().get(Project.id == project_id)
    user: BaseUser = await BaseUser.objects().get(BaseUser.id == user_id)
    await project.update_from_source(user)


async def tick(_):
    print(f"tick {datetime.datetime.now(datetime.timezone.utc)}")


SAQ_SETTINGS = {
    "queue": SAQ_QUEUE,
    "functions": [run_scanners, update_from_source, git_clone],
    "concurrency": 10,
    "cron_jobs": [CronJob(tick, cron="* * * * * */5")],  # run every 5 seconds
}
