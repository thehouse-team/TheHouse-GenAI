"""HTTP middleware for request correlation, structured access logs and size limits."""

from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from thehouse_genai.api.errors import error_response
from thehouse_genai.api.request_context import (
    get_request_id,
    request_id_ctx,
    sanitize_request_id,
)

logger = logging.getLogger(__name__)

_PATH_ID_PATTERN = re.compile(r"\b[0-9a-fA-F]{8,}\b")


class RequestContextMiddleware:
    """Attach a safe request ID, echo it, and emit one structured access log."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = sanitize_request_id(headers.get("x-request-id")) or uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_ctx.set(request_id)
        started = perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "http.request.completed",
                extra={
                    "request_id": request_id,
                    "method": scope.get("method", ""),
                    "path": _PATH_ID_PATTERN.sub("{id}", scope.get("path", "")),
                    "status_code": status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                },
            )
            request_id_ctx.reset(token)


class RequestTooLargeError(Exception):
    """Raised internally when a streamed body exceeds the configured limit."""


class RequestSizeLimitMiddleware:
    """Reject oversized request bodies before they reach application code."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        declared = headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send, message="Invalid Content-Length header.")
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLargeError:
            await self._reject(send)

    async def _reject(self, send: Send, *, message: str = "Request body too large.") -> None:
        response = error_response(
            status_code=413,
            code="PAYLOAD_TOO_LARGE",
            message=message,
            request_id=get_request_id(),
        )
        await response(
            scope={"type": "http"},
            receive=_empty_receive,
            send=send,
        )


async def _empty_receive() -> Message:
    return {"type": "http.disconnect"}
