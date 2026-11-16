"""Service-to-service authentication for generative endpoints."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request

from thehouse_genai.infrastructure.config import Settings, get_settings


def require_service_auth(
    request: Request,
    x_service_key: str | None = Header(default=None, alias="X-Service-Key"),
) -> None:
    """Require a valid service key for protected generative endpoints."""

    settings: Settings = getattr(request.app.state, "settings", get_settings())
    expected = settings.service_api_key
    if expected is None or x_service_key is None:
        raise HTTPException(status_code=401, detail="UNAUTHORIZED")
    provided = x_service_key.encode("utf-8")
    secret = expected.get_secret_value().encode("utf-8")
    if not hmac.compare_digest(provided, secret):
        raise HTTPException(status_code=401, detail="UNAUTHORIZED")
