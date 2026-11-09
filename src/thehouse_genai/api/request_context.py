"""Request identity and safe correlation helpers."""

from __future__ import annotations

import re
from contextvars import ContextVar

from fastapi import Request

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def sanitize_request_id(value: str | None) -> str | None:
    """Accept only short, log-safe client correlation IDs."""

    if value is None:
        return None
    candidate = value.strip()
    if _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return None


def get_request_id(request: Request | None = None) -> str:
    """Return the request correlation ID, or a neutral fallback outside a request."""

    if request is not None:
        value = getattr(request.state, "request_id", None)
        if isinstance(value, str) and value:
            return value
    return request_id_ctx.get()
