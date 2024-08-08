from typing import Literal

from litestar import Request
from litestar.connection import ASGIConnection
from litestar.plugins.flash import flash
from piccolo.apps.user.tables import BaseUser


def alert(
    request,
    message,
    level: Literal["info", "warning", "error", "success"] = "info",
):
    """A helper function given we hard code level in templates"""
    flash(request, message, category=level)


async def inject_alerts(request: Request | ASGIConnection, user: BaseUser):
    """Ensure lazy notifications mate it through"""
    from home.tables import Notification

    alerts_to_show: list[Notification] = await Notification.objects().where(
        Notification.target == user
    )
    for notification in alerts_to_show:
        alert(request, notification.message, notification.level)
        await notification.delete().where(Notification.id == notification.uuid)
