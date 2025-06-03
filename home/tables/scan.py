from __future__ import annotations

import datetime
import typing
import uuid

from piccolo.apps.user.tables import BaseUser
from piccolo.columns import (
    UUID,
    ForeignKey,
    Integer,
    Timestamptz,
    LazyTableReference,
    Array,
    Text,
)
from piccolo.table import Table
import arrow

if typing.TYPE_CHECKING:
    from home.tables import Project, Vulnerability


class Scan(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    created_at = Timestamptz(help_text="When the scan was initially created")
    project = ForeignKey(
        LazyTableReference("Project", app_name="home"),
        index=True,
        help_text="The project this scan was run for",
    )
    number = Integer(
        index=True,
        help_text="What number scan this is, in relation to a specific project",
    )
    scanner_versions_used = Array(
        base_column=Text(),
        help_text="A list of <Scanner <Version>> for each scanner used for this scan.",
    )

    @property
    def scanned_at(self) -> datetime.datetime:
        return self.created_at

    @property
    def uuid(self) -> str:
        return str(self.id)

    @property
    def scanner_versions(self) -> str:
        """Returns the version of scanners used."""
        return_str = ", ".join(self.scanner_versions_used)
        if not return_str:
            return "Unknown"

        return return_str

    @classmethod
    async def get_next_number(cls, project: Project) -> int:
        """Fetches the next scan number for a given project"""
        count = await Scan.count().where(Scan.project == project)
        return count + 1

    async def export_as_json(self, requester: BaseUser) -> dict[str, ...]:
        """Export this scan as a JSON object."""
        from home.tables import Vulnerability

        base_data = (
            await Scan.select(
                Scan.project.all_columns(
                    exclude=[Scan.project.directory, Scan.project.other_users]
                ),
                Scan.project.owner.username,
                Scan.project.owner.first_name,
                Scan.project.owner.last_name,
                Scan.project.owner.email,
                Scan.all_columns(exclude=["number", "created_at"]),
                Scan.number.as_alias("scan_number"),
                Scan.created_at.as_alias("scanned_at"),
            )
            .output(nested=True)
            .where(Scan.id == self.id)
            .first()
        )
        vulns = await Vulnerability.select(
            Vulnerability.all_columns(exclude=["project", "scan"])
        ).where(Vulnerability.scan == self)
        base_data["vulnerabilities"] = vulns

        data = {
            "scan": base_data,
            "archive_created_at": arrow.utcnow().datetime,
            "archive_creator": {
                "username": requester.username,
                "first_name": requester.first_name,
                "last_name": requester.last_name,
                "email": requester.email,
            },
        }
        return data
