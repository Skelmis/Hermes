from litestar import Controller, Request, post, get, MediaType
from litestar.response import Redirect, Template
from piccolo_api.session_auth.tables import SessionsBase
from piccolo_api.shared.auth.styles import Styles
from starlette.status import HTTP_303_SEE_OTHER

from home.custom_request import HermesRequest
from home.util import get_csp


class LogoutController(Controller):
    path = "/logout"
    _session_table = SessionsBase
    _redirect_to = "/"
    _cookie_name = "id"
    _styles = Styles()

    def _render_template(self, request: HermesRequest) -> Template:
        # If CSRF middleware is present, we have to include a form field with
        # the CSRF token. It only works if CSRFMiddleware has
        # allow_form_param=True, otherwise it only looks for the token in the
        # header.
        csp, nonce = get_csp()
        csrftoken = request.scope.get("csrftoken")  # type: ignore
        csrf_cookie_name = request.scope.get("csrf_cookie_name")  # type: ignore

        return Template(
            "auth/logout.jinja",
            context={
                "csrftoken": csrftoken,
                "csrf_cookie_name": csrf_cookie_name,
                "request": request,
                "styles": self._styles,
                "active": "vulnerabilities",
                "is_small": request.is_small,
                "csp_nonce": nonce,
            },
            media_type=MediaType.HTML,
            headers={"content-security-policy": csp},
        )

    @classmethod
    async def logout_current_user(cls, request: Request) -> Redirect:
        cookie = request.cookies.get(cls._cookie_name, None)
        if not cookie:
            # Meh this is fine, just redirect it to home
            return Redirect("/")

        await cls._session_table.remove_session(token=cookie)

        response: Redirect = Redirect(cls._redirect_to, status_code=HTTP_303_SEE_OTHER)

        response.set_cookie(cls._cookie_name, "", max_age=0)
        return response

    @get(include_in_schema=False, name="signout")
    async def get(self, request: HermesRequest) -> Template:
        return self._render_template(request)

    @post(tags=["Auth"])
    async def post(self, request: Request) -> Redirect:
        return await self.logout_current_user(request)
