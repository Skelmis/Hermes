from litestar import Response, MediaType
from litestar.exceptions import NotFoundException
from litestar.response import Redirect, Template


class RedirectForAuth(Exception):
    """Mark this authentication failure as a request to receive it"""

    def __init__(self, next_route: str):
        self.next_route = next_route


def redirect_for_auth(_, exc: RedirectForAuth) -> Response[Redirect]:
    """Where auth is required, redirect for it"""
    return Redirect(f"/login?next_route={exc.next_route}")


def handle_404(_, __: NotFoundException) -> Template:
    return Template(
        "errors/404.jinja",
        media_type=MediaType.HTML,
    )


def handle_500(_, __: NotFoundException) -> Template:
    return Template(
        "errors/500.jinja",
        media_type=MediaType.HTML,
    )
