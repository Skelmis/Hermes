from __future__ import annotations

import uuid

from piccolo.columns import (
    UUID,
    ForeignKey,
    Timestamptz,
    Interval,
    LazyTableReference,
)
from piccolo.table import Table


class ProjectAutomation(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    project = ForeignKey(
        LazyTableReference("Project", app_name="home"),
        index=True,
        help_text="The project this automation is for",
    )
    scan_interval = Interval(
        default=None, null=True, help_text="How often to run a code scan"
    )
    last_scanned_at = Timestamptz(help_text="When was the last scan ran?")
    pull_interval = Interval(
        default=None, null=True, help_text="How often to pull source code"
    )
    last_pulled_at = Timestamptz(help_text="When was the code last pulled?")
