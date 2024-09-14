from litestar import Request
from litestar.connection.base import empty_receive, empty_send
from litestar.types import Scope, Send, Receive


class HermesRequest(Request):
    """Extends the request object to add custom metadata"""

    __slots__ = ("is_small",)

    def __init__(
        self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send
    ) -> None:
        """Initialize CustomRequest class."""
        super().__init__(scope=scope, receive=receive, send=send)
        self.is_small = "is_small" in scope.get("query_string", b"").decode()
