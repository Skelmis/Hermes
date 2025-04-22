from __future__ import annotations

import datetime
import uuid

import arrow
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

    @classmethod
    async def get_or_create(cls, user: BaseUser) -> Profile:
        return await Profile.objects().get_or_create(Profile.target == user)

    def localize_dt(self, value: datetime.datetime | str):
        """Given a UTC dt, normalize to the users profile"""
        if isinstance(value, str):
            # To handle flexible archive schemas
            value = arrow.get(value).datetime

        def tz_aware(dt):
            return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

        if not tz_aware(value):
            raise ValueError("Application was given a timezone naive DT")

        timezone = pytz.timezone(self.timezone)
        return value.astimezone(timezone)
