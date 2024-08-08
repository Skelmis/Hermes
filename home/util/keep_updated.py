from datetime import datetime, timezone
from home.tables import Project


async def keep_projects_updated():
    print(f"tick {datetime.now(timezone.utc)}")
