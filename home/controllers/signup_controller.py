import re
import typing as t
from hmac import compare_digest

from commons.hibp import has_password_been_pwned
from litestar import Controller, get, Request, post, MediaType
from litestar.exceptions import SerializationException
from litestar.response import Template, Redirect
from piccolo.apps.user.tables import BaseUser

from home.util import get_csp
from home.util.flash import alert
from home.configs import ALLOW_REGISTRATION

SIMPLE_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class SignUpController(Controller):
    path = "/signup"

    @get(include_in_schema=False, name="signup")
    async def get(self, request: Request) -> Template:
        if not ALLOW_REGISTRATION:
            alert(
                request,
                "Sign ups are disabled. This will do nothing.",
                level="warning",
            )

        csp, nonce = get_csp()
        return Template(
            "auth/signup.jinja",
            context={
                "csp_nonce": nonce,
            },
            media_type=MediaType.HTML,
            headers={"content-security-policy": csp},
        )

    @post(tags=["Auth"])
    async def post(
        self, request: Request, next_route: str = "/"
    ) -> Template | Redirect:
        if not ALLOW_REGISTRATION:
            return Redirect("/signup")

        # Some middleware (for example CSRF) has already awaited the request
        # body, and adds it to the request.
        body: t.Any = request.scope.get("form")  # type: ignore

        if not body:
            try:
                body = await request.json()
            except SerializationException:
                body = await request.form()

        email = body.get("email", None)
        username = body.get("username", None)
        password = body.get("password", None)
        confirm_password = body.get("confirm_password", None)

        if (not username) or (not password) or (not confirm_password) or (not email):
            error_message = "Please ensure all fields on the form are filled out."
            alert(request, error_message, level="error")
            return Template(
                "auth/signup.jinja",
                media_type=MediaType.HTML,
            )

        if not SIMPLE_EMAIL_REGEX.match(email):
            alert(request, "Please enter a valid email.", level="error")
            return Template(
                "auth/signup.jinja",
                media_type=MediaType.HTML,
            )

        if not compare_digest(password, confirm_password):
            alert(request, "Passwords do not match", level="error")
            return Template(
                "auth/signup.jinja",
                media_type=MediaType.HTML,
            )

        if await has_password_been_pwned(password):
            alert(
                request,
                "This password appears in breach databases, "
                "please pick a unique password.",
                level="error",
            )
            return Template(
                "auth/signup.jinja",
                media_type=MediaType.HTML,
            )

        if await BaseUser.exists().where(
            BaseUser.username == username,  # type: ignore
        ):
            alert(
                request,
                "This user already exists, consider signing in instead.",
                level="error",
            )
            return Template(
                "auth/signup.jinja",
                media_type=MediaType.HTML,
            )

        try:
            user: BaseUser = await BaseUser.create_user(
                username, password, email=email, active=True
            )
        except ValueError as err:
            alert(request, str(err), level="error")
            return Template(
                "auth/signup.jinja",
                media_type=MediaType.HTML,
            )

        if await BaseUser.count() == 1:
            alert(
                request,
                "Thanks for creating an account, you may now log in. "
                "As you are the first user on the system, I have also made you an admin user.",
                level="success",
            )
            user.admin = True
            await user.save()

        else:
            alert(
                request,
                "Thanks for creating an account, you may now log in.",
                level="success",
            )

        return Redirect(request.url_for("login"))
