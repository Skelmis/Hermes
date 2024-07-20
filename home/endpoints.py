import os

import jinja2
from litestar import MediaType, Request, Response, get

from home.util import get_csp

ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        searchpath=os.path.join(os.path.dirname(__file__), "templates")
    ),
    autoescape=True,
)


@get(path="/", include_in_schema=False, sync_to_thread=False)
def home(request: Request) -> Response:
    csp, nonce = get_csp()
    template = ENVIRONMENT.get_template("home.jinja")
    content = template.render(
        projects=[{"id": "1", "title": "Project one"}], csp_nonce=nonce
    )
    return Response(
        content,
        media_type=MediaType.HTML,
        status_code=200,
        headers={"content-security-policy": csp},
    )
