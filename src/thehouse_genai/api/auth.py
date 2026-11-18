"""Minimal service-to-service authentication for generative endpoints.

The credential is held as a `SecretStr` in `Settings` and compared in constant time.
Every rejection produces the same safe 401 envelope, so a caller cannot distinguish a
missing header, a wrong value and an unconfigured credential.
"""

from __future__ import annotations

import hmac
from typing import Final

from fastapi import HTTPException, Request

from thehouse_genai.infrastructure.config import Settings

_SERVICE_KEY_HEADER: Final = "x-service-key"


def require_service_key(request: Request) -> None:
    """Reject requests without a valid `X-Service-Key` header.

    Raises:
        HTTPException: 401 with the standard error envelope on any rejection.
    """

    settings: Settings = request.app.state.settings
    expected = settings.service_key
    presented = request.headers.get(_SERVICE_KEY_HEADER)
    valid = (
        expected is not None
        and presented is not None
        and hmac.compare_digest(
            presented.encode("utf-8"),
            expected.get_secret_value().encode("utf-8"),
        )
    )
    if not valid:
        raise HTTPException(status_code=401)
