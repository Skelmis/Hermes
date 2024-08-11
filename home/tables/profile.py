import datetime
import uuid

import pytz
from piccolo.apps.user.tables import BaseUser
from piccolo.columns import ForeignKey, UUID, Text
from piccolo.table import Table


class Profile(Table):
    id = UUID(primary_key=True, default=uuid.uuid4, index=True)
    target = ForeignKey(
        BaseUser, unique=True, index=True, help_text="Who this profile is for"
    )
    timezone = Text(default="Pacific/Auckland")

    def localize_dt(self, value: datetime.datetime):
        """Given a UTC dt, normalize to the users profile"""

        def tz_aware(dt):
            return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

        if not tz_aware(value):
            raise ValueError("Application was given a timezone naive DT")

        timezone = pytz.timezone(self.timezone)
        return value.astimezone(timezone)
