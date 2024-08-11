from __future__ import annotations

import uuid
from enum import Enum

from piccolo.apps.user.tables import BaseUser
from piccolo.columns import (
    UUID,
    ForeignKey,
    Text,
)
from piccolo.table import Table


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
