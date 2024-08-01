import os
import typing as t

from jinja2 import Environment, FileSystemLoader
from litestar import Controller, Request, post, get
from piccolo.apps.user.tables import BaseUser
from piccolo_api.session_auth.endpoints import LOGOUT_TEMPLATE_PATH
from piccolo_api.session_auth.tables import SessionsBase
from piccolo_api.shared.auth.styles import Styles
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

directory, filename = os.path.split(LOGOUT_TEMPLATE_PATH)
environment = Environment(loader=FileSystemLoader(directory), autoescape=True)
login_template = environment.get_template(filename)


# Taken from the underlying Piccolo class and modified to work with Litestar
class LogoutController(Controller):
    path = "/logout"
    _auth_table = BaseUser
    _session_table = SessionsBase
    _redirect_to = "/"
    _cookie_name = "id"
    _logout_template = login_template
    _styles = Styles()

    def _render_template(
        self, request: Request, template_context: t.Dict[str, t.Any] = {}
    ) -> HTMLResponse:
        # If CSRF middleware is present, we have to include a form field with
        # the CSRF token. It only works if CSRFMiddleware has
        # allow_form_param=True, otherwise it only looks for the token in the
        # header.
        csrftoken = request.scope.get("csrftoken")
        csrf_cookie_name = request.scope.get("csrf_cookie_name")

        return HTMLResponse(
            self._logout_template.render(
                csrftoken=csrftoken,
                csrf_cookie_name=csrf_cookie_name,
                request=request,
                styles=self._styles,
                **template_context,
            )
        )

    @get()
    async def get(self, request: Request) -> HTMLResponse:
        return self._render_template(request)

    @post()
    async def post(self, request: Request) -> RedirectResponse:
        cookie = request.cookies.get(self._cookie_name, None)
        if not cookie:
            raise HTTPException(
                status_code=401, detail="The session cookie wasn't found."
            )
        await self._session_table.remove_session(token=cookie)

        response: RedirectResponse = RedirectResponse(
            url=self._redirect_to, status_code=HTTP_303_SEE_OTHER
        )

        response.set_cookie(self._cookie_name, "", max_age=0)
        return response
