import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from kasta_api.core.config import get_settings
from kasta_api.core.context import request_id_context

logger = logging.getLogger(__name__)


class ValidationIssue(BaseModel):
    location: list[str | int]
    message: str
    code: str


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str
    request_id: str
    errors: list[ValidationIssue] | None = Field(default=None)


def request_id_from(request: Request) -> str:
    return str(getattr(request.state, "request_id", request_id_context.get()))


def problem_response(
    request: Request,
    *,
    status_code: int,
    detail: str,
    title: str | None = None,
    errors: list[ValidationIssue] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = request_id_from(request)
    response_headers = dict(headers or {})
    response_headers[get_settings().request_id_header] = request_id
    problem = ProblemDetail(
        title=title or _status_title(status_code),
        status=status_code,
        detail=detail,
        instance=request.url.path,
        request_id=request_id,
        errors=errors,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(mode="json", exclude_none=True),
        media_type="application/problem+json",
        headers=response_headers,
    )


def internal_server_error_response(request: Request) -> JSONResponse:
    return problem_response(
        request,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail="Terjadi kesalahan internal. Silakan coba kembali.",
    )


async def handle_http_exception(request: Request, exception: Exception) -> Response:
    if not isinstance(exception, StarletteHTTPException):
        raise TypeError("HTTP exception handler menerima tipe yang tidak sesuai")
    detail = (
        exception.detail
        if isinstance(exception.detail, str)
        else "Permintaan tidak dapat diproses."
    )
    return problem_response(
        request,
        status_code=exception.status_code,
        detail=detail,
        headers=exception.headers,
    )


async def handle_validation_exception(request: Request, exception: Exception) -> Response:
    if not isinstance(exception, RequestValidationError):
        raise TypeError("Validation handler menerima tipe yang tidak sesuai")
    issues = [
        ValidationIssue(
            location=[_serializable_location(part) for part in error["loc"]],
            message=error["msg"],
            code=error["type"],
        )
        for error in exception.errors()
    ]
    return problem_response(
        request,
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        title="Data tidak valid",
        detail="Periksa kembali data yang dikirim.",
        errors=issues,
    )


async def handle_unexpected_exception(request: Request, exception: Exception) -> Response:
    logger.exception("Unhandled application error", exc_info=exception)
    return internal_server_error_response(request)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_exception)
    app.add_exception_handler(Exception, handle_unexpected_exception)


def _status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Error"


def _serializable_location(value: Any) -> str | int:
    return value if isinstance(value, (str, int)) else str(value)
