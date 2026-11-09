"""Consistent, non-leaking API error responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from thehouse_genai.api.request_context import get_request_id

logger = logging.getLogger(__name__)

_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}

_SAFE_MESSAGES = {
    400: "Bad request.",
    401: "Authentication required.",
    403: "Access denied.",
    404: "Resource not found.",
    405: "Method not allowed.",
    409: "Request conflicts with current state.",
    413: "Request body too large.",
    422: "Request validation failed.",
    429: "Too many requests.",
    500: "Internal server error.",
    503: "Service unavailable.",
}


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
) -> JSONResponse:
    """Build the single error envelope used by every endpoint."""

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


def install_exception_handlers(app: FastAPI) -> None:
    """Register handlers that never expose stack traces or exception details."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return error_response(
            status_code=exc.status_code,
            code=_ERROR_CODES.get(exc.status_code, "HTTP_ERROR"),
            message=_SAFE_MESSAGES.get(exc.status_code, "Request could not be completed."),
            request_id=get_request_id(request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            request_id=get_request_id(request),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
        request_id = get_request_id(request)
        logger.exception(
            "unhandled_exception",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error.",
            request_id=request_id,
        )
