import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from kasta_api.core.context import request_id_context
from kasta_api.core.errors import internal_server_error_response

logger = logging.getLogger(__name__)
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled request error")
            return internal_server_error_response(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, header_name: str) -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = self._request_id(request)
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started_at = perf_counter()

        try:
            response = await call_next(request)
            response.headers[self.header_name] = request_id
            logger.info(
                "HTTP request completed",
                extra={
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                },
            )
            return response
        finally:
            request_id_context.reset(token)

    def _request_id(self, request: Request) -> str:
        candidate = request.headers.get(self.header_name, "")
        return candidate if _SAFE_REQUEST_ID.fullmatch(candidate) else str(uuid4())
