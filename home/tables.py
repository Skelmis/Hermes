from __future__ import annotations

import asyncio
import datetime
import logging
import subprocess
import uuid
from enum import Enum
from typing import Type

import commons
from litestar.response import Redirect
from piccolo.apps.user.tables import BaseUser
from piccolo.table import Table
from piccolo.columns import (
    UUID,
    ForeignKey,
    Text,
    Integer,
    Boolean,
    Array,
    Timestamptz,
    Interval,
)

from home.util.flash import alert

log = logging.getLogger(__name__)


class NotificationLevels(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

    @classmethod
    def from_str(cls, level) -> NotificationLevels:
        return cls[level.upper()]


class Notification(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    target = ForeignKey(BaseUser, index=True, help_text="Who should be notified")
    message = Text(help_text="The text to show on next request")
    level = Text(help_text="The level to show it at", choices=NotificationLevels)

    @property
    def uuid(self) -> str:
        return str(self.id)

    @classmethod
    async def create_alert(
        cls, user: BaseUser, message: str, level: str
    ) -> Notification:
        notif = Notification(
            target=user,
            message=message,
            level=level,
        )
        await notif.save()
        return notif


class Project(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    owner = ForeignKey(BaseUser, index=True, help_text="Who owns this project")
    created_at = Timestamptz(help_text="When the project was created")
    title = Text()
    description = Text(default="")
    directory = Text(default="", help_text="The path to this project on disk")
    is_git_based = Boolean(
        default=False,
        help_text="Denotes if the underlying stuff is git based "
        "and is used as a check before performing git actions",
    )
    code_scanners = Array(
        base_column=Text(),
        help_text="A list of Analysis Interface id's to use",
    )

    @property
    def scanner_path(self) -> str:
        """The path input to a given scanner"""
        from piccolo_conf import BASE_PROJECT_DIR

        return str(BASE_PROJECT_DIR / self.directory)

    def normalize_finding_path(self, file_path: str) -> str:
        """Remove the metadata paths from findings"""
        return file_path.removeprefix(f"{self.scanner_path}/")

    @property
    def uuid(self) -> str:
        return str(self.id)

    def redirect_to(self) -> Redirect:
        return Redirect(f"/projects/{self.uuid}")

    async def update_from_source(self, request) -> None:
        """Updates the underlying source code

        Notes
        -----
        Designed to be run in the background
        due to how long it may take
        """
        if not self.is_git_based:
            raise ValueError("Cannot update a non git based project")

        fetch = ["git", "fetch"]
        pull = ["git", "pull"]
        try:
            subprocess.check_output(fetch, cwd=self.scanner_path)
            subprocess.check_output(pull, cwd=self.scanner_path)
        except Exception as e:
            await Notification.create_alert(
                request.user,
                f"Something went wrong pulling project '{self.title}', check the logs",
                level="error",
            )
            log.error("Git cloning died with error\n%s", commons.exception_as_string(e))
        else:
            pa: ProjectAutomation | None = (
                await ProjectAutomation.objects()
                .where(ProjectAutomation.project == self)
                .first()
            )
            if pa:
                pa.last_pulled_at = datetime.datetime.now(tz=datetime.timezone.utc)
                await pa.save()

        await Notification.create_alert(
            request.user,
            f"Successfully pulled project '{self.title}'",
            level="success",
        )

    async def run_scanners(self, request) -> Redirect:
        """Run all the relevant scanners for this project.

        Notes
        -----
        Designed to be run in the background
        due to how long it may take
        """
        from piccolo_conf import REGISTERED_INTERFACES
        from home.analysis import AnalysisInterface

        fail_count = 0
        scan = Scan(
            project=self,
            number=await Scan.get_next_number(self),
        )
        await scan.save()
        for interface_id in self.code_scanners:
            interface: Type[AnalysisInterface] | None = REGISTERED_INTERFACES.get(
                interface_id
            )
            if interface is None:
                await Notification.create_alert(
                    request.user,
                    f"Failed to find an interface with id {interface_id}",
                    level="error",
                )
                fail_count += 1
                continue

            instance = interface(self)
            await instance.scan(scan)

        if fail_count == len(self.code_scanners):
            await Notification.create_alert(
                request.user,
                f"Looks like all interfaces could not be found."
                f" Ran nothing for project '{self.title}'",
                level="error",
            )
        else:
            await Notification.create_alert(
                request.user,
                f"Successfully ran found scanners against project '{self.title}'",
                level="success",
            )

        pa: ProjectAutomation | None = (
            await ProjectAutomation.objects()
            .where(ProjectAutomation.project == self)
            .first()
        )
        if pa:
            pa.last_scanned_at = datetime.datetime.now(tz=datetime.timezone.utc)
            await pa.save()

        return Redirect(f"/projects/{self.uuid}")


class ProjectAutomation(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    project = ForeignKey(
        Project,
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


class Scan(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    created_at = Timestamptz(help_text="When the scan was initially created")
    project = ForeignKey(
        Project,
        index=True,
        help_text="The project this scan was run for",
    )
    number = Integer(
        index=True,
        help_text="What number scan this is, in relation to a specific project",
    )

    @property
    def uuid(self) -> str:
        return str(self.id)

    @classmethod
    async def get_next_number(cls, project: Project) -> int:
        """Fetches the next scan number for a given project"""
        count = await Scan.count().where(Scan.project == project)
        return count + 1


# TODO Add status fields
class Vulnerability(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    created_at = Timestamptz(help_text="When the vulnerability was created")
    scan = ForeignKey(
        Scan,
        index=True,
        help_text="The scan this vulnerability exists as",
    )
    project = ForeignKey(
        Project,
        index=True,
        help_text="The project this vulnerability belongs to",
    )
    title = Text()
    description = Text(default="")
    impact = Text(default="", help_text="The scanner disclosed impact of this result")
    likelihood = Text(
        default="", help_text="The scanner disclosed likelihood of this result"
    )
    severity = Text(
        default="", help_text="The scanner disclosed severity of this result"
    )
    confidence = Text(
        default="", help_text="How confident the scanner is about this result"
    )
    code_file = Text(
        default="",
        help_text="A path to the code at fault",
    )
    code_line = Text(
        default="",
        help_text="The line of code which threw this error",
    )
    code_context = Text(
        default="",
        help_text="The code related to this issue",
    )
    found_by = Text(
        default="Unknown",
        help_text="The analysis interface that found this vulnerability",
    )

    @property
    def uuid(self) -> str:
        return str(self.id)
