from litestar import Controller, get, MediaType, Request, post
from litestar.response import Template, Redirect

from home.util import get_csp
from home.util.flash import alert


class PasswordController(Controller):
    path = "/passwords"

    @get(include_in_schema=False, name="forgot_password", path="/forgot")
    async def forgot_password_get(self, request: Request) -> Template:
        alert(
            request,
            "This functionality hasn't been implemented yet. "
            "Reach out to your administrator.",
            level="info",
        )
        csp, nonce = get_csp()
        return Template(
            "auth/forgot_password.jinja",
            context={
                "csp_nonce": nonce,
            },
            media_type=MediaType.HTML,
            headers={"content-security-policy": csp},
        )

    @post(tags=["Auth"], path="/forgot")
    async def forgot_password_post(self, request: Request) -> Redirect:
        return Redirect("/passwords/forgot")
