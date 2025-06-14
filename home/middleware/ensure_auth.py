from __future__ import annotations

import os
import secrets

from commons import value_to_bool
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.middleware import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from piccolo.apps.user.tables import BaseUser
from piccolo_api.session_auth.tables import SessionsBase

from home.exception_handlers import RedirectForAuth
from home.util.flash import alert, inject_alerts


class EnsureAuth(AbstractAuthenticationMiddleware):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.auth_table = BaseUser
        self.session_table = SessionsBase
        self.cookie_name = "id"
        self.admin_only = False
        self.superuser_only = False
        self.active_only = True
        self.increase_expiry = None
        self.auth_is_disabled = value_to_bool(os.environ.get("DISABLE_AUTH", False))

    async def authenticate_request(
        self, connection: ASGIConnection
    ) -> AuthenticationResult:
        if self.auth_is_disabled:
            user: BaseUser | None = await BaseUser.objects().get(
                BaseUser.username == "hermes"  # type: ignore
            )
            if user is None:
                user = await BaseUser.create_user(
                    "hermes",
                    password=secrets.token_hex(32),
                )

            return AuthenticationResult(user=user, auth=None)

        possible_redirect = (
            f"{connection.url.path}?{connection.url.query}"
            if connection.url.query
            else connection.url.path
        )
        token = connection.cookies.get(self.cookie_name, None)
        if not token:
            alert(connection, "Please authenticate to view this resource")
            raise RedirectForAuth(possible_redirect)

        user_id = await self.session_table.get_user_id(
            token, increase_expiry=self.increase_expiry
        )

        if not user_id:
            alert(connection, "Please authenticate to view this resource")
            raise RedirectForAuth(possible_redirect)

        piccolo_user = (
            await self.auth_table.objects()
            .where(self.auth_table._meta.primary_key == user_id)
            .first()
            .run()
        )

        if not piccolo_user:
            # Used to say "That user doesn't exist anymore"
            raise NotAuthorizedException("That user doesn't exist")

        if self.admin_only and not piccolo_user.admin:
            raise NotAuthorizedException("Admin users only")

        if self.superuser_only and not piccolo_user.superuser:
            raise NotAuthorizedException("Superusers only")

        if self.active_only and not piccolo_user.active:
            raise NotAuthorizedException("Active users only")

        await inject_alerts(connection, piccolo_user)

        return AuthenticationResult(user=piccolo_user, auth=None)
