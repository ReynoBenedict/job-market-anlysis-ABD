"""One error envelope for every failure: {"error": {code, message, details, request_id}}.
Internal exceptions are logged with the request ID and never echoed to clients."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from talentscope.api.schemas import ErrorBody, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _response(
    request: Request, status: int, code: str, message: str, details: list[ErrorDetail] | None = None
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=details or [],
            request_id=getattr(request.state, "request_id", None),
        )
    )
    return JSONResponse(status_code=status, content=body.model_dump())


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return _response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            ErrorDetail(
                field=".".join(str(part) for part in err["loc"][1:]) or None, message=err["msg"]
            )
            for err in exc.errors()
        ]
        return _response(
            request, 422, "invalid_request", "Request parameters are invalid.", details
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = "Resource not found." if exc.status_code == 404 else str(exc.detail)
        return _response(request, exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled error",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
            },
        )
        return _response(request, 500, "internal_error", "An unexpected error occurred.")
