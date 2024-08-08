from datetime import datetime, timezone

from apscheduler import task


@task(max_running_jobs=1)
async def keep_projects_updated():
    print(f"tick {datetime.now(timezone.utc)}")
