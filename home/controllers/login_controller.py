import os
import typing as t
import warnings
from datetime import timedelta, datetime

from jinja2 import Environment, FileSystemLoader
from litestar import Controller, get, Request, post
from litestar.exceptions import SerializationException
from piccolo.apps.user.tables import BaseUser
from piccolo_api.session_auth.endpoints import LOGIN_TEMPLATE_PATH
from piccolo_api.session_auth.tables import SessionsBase
from piccolo_api.shared.auth.styles import Styles
from starlette.exceptions import HTTPException
from starlette.responses import (
    HTMLResponse,
    Response,
    PlainTextResponse,
    RedirectResponse,
    JSONResponse,
)
from starlette.status import HTTP_303_SEE_OTHER

directory, filename = os.path.split(LOGIN_TEMPLATE_PATH)
environment = Environment(loader=FileSystemLoader(directory), autoescape=True)
login_template = environment.get_template(filename)


# Taken from the underlying Piccolo class and modified to work with Litestar
class LoginController(Controller):
    path = "/login"
    _auth_table = BaseUser
    _session_table = SessionsBase
    _session_expiry = timedelta(hours=1)
    _max_session_expiry = timedelta(days=1)
    _redirect_to = "/"
    _production = not bool(os.environ.get("DEBUG", False))
    _cookie_name = "id"
    _login_template = login_template
    _hooks = None
    _captcha = None
    _styles = Styles()

    def _render_template(
        self,
        request: Request,
        template_context: t.Dict[str, t.Any] = {},
        status_code=200,
    ) -> HTMLResponse:
        # If CSRF middleware is present, we have to include a form field with
        # the CSRF token. It only works if CSRFMiddleware has
        # allow_form_param=True, otherwise it only looks for the token in the
        # header.
        csrftoken = request.scope.get("csrftoken")
        csrf_cookie_name = request.scope.get("csrf_cookie_name")

        return HTMLResponse(
            self._login_template.render(
                csrftoken=csrftoken,
                csrf_cookie_name=csrf_cookie_name,
                request=request,
                captcha=self._captcha,
                styles=self._styles,
                **template_context,
            ),
            status_code=status_code,
        )

    def _get_error_response(
        self, request, error: str, response_format: t.Literal["html", "plain"]
    ) -> Response:
        if response_format == "html":
            return self._render_template(
                request, template_context={"error": error}, status_code=401
            )
        else:
            return PlainTextResponse(status_code=401, content=f"Login failed: {error}")

    @get(include_in_schema=False)
    async def get(self, request: Request) -> HTMLResponse:
        return self._render_template(request)

    @post()
    async def post(self, request: Request, next_route: str = "/") -> Response:
        # Some middleware (for example CSRF) has already awaited the request
        # body, and adds it to the request.
        body: t.Any = request.scope.get("form")

        if not body:
            try:
                body = await request.json()
            except SerializationException:
                body = await request.form()

        username = body.get("username", None)
        password = body.get("password", None)
        return_html = body.get("format") == "html"

        if (not username) or (not password):
            error_message = "Missing username or password"
            if return_html:
                return self._render_template(
                    request,
                    template_context={"error": error_message},
                )
            else:
                raise HTTPException(status_code=422, detail=error_message)

        # Run pre_login hooks
        if self._hooks and self._hooks.pre_login:
            hooks_response = await self._hooks.run_pre_login(username=username)
            if isinstance(hooks_response, str):
                return self._get_error_response(
                    request=request,
                    error=hooks_response,
                    response_format="html" if return_html else "plain",
                )

        # Check CAPTCHA
        if self._captcha:
            token = body.get(self._captcha.token_field, None)
            validate_response = await self._captcha.validate(token=token)
            if isinstance(validate_response, str):
                if return_html:
                    return self._render_template(
                        request,
                        template_context={"error": validate_response},
                    )
                else:
                    raise HTTPException(status_code=401, detail=validate_response)

        # Attempt login
        user_id = await self._auth_table.login(username=username, password=password)

        if user_id:
            # Run login_success hooks
            if self._hooks and self._hooks.login_success:
                hooks_response = await self._hooks.run_login_success(
                    username=username, user_id=user_id
                )
                if isinstance(hooks_response, str):
                    return self._get_error_response(
                        request=request,
                        error=hooks_response,
                        response_format="html" if return_html else "plain",
                    )
        else:
            # Run login_failure hooks
            if self._hooks and self._hooks.login_failure:
                hooks_response = await self._hooks.run_login_failure(username=username)
                if isinstance(hooks_response, str):
                    return self._get_error_response(
                        request=request,
                        error=hooks_response,
                        response_format="html" if return_html else "plain",
                    )

            if return_html:
                return self._render_template(
                    request,
                    template_context={
                        "error": "The username or password is incorrect."
                    },
                )
            else:
                raise HTTPException(status_code=401, detail="Login failed")

        now = datetime.now()
        expiry_date = now + self._session_expiry
        max_expiry_date = now + self._max_session_expiry

        session: SessionsBase = await self._session_table.create_session(
            user_id=user_id,
            expiry_date=expiry_date,
            max_expiry_date=max_expiry_date,
        )

        response: Response = RedirectResponse(
            url=next_route, status_code=HTTP_303_SEE_OTHER
        )

        if not self._production:
            message = (
                "If running sessions in production, make sure 'production' "
                "is set to True, and serve under HTTPS."
            )
            warnings.warn(message)

        cookie_value = t.cast(str, session.token)

        response.set_cookie(
            key=self._cookie_name,
            value=cookie_value,
            httponly=True,
            secure=self._production,
            max_age=int(self._max_session_expiry.total_seconds()),
            samesite="lax",
        )
        return response
