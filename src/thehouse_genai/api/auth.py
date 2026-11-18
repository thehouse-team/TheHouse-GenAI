"""Service-to-service authentication for generative endpoints.

The current credential and, during rotation, the previous one are held as `SecretStr`
in `Settings`. Every configured key is compared in constant time on every request, so
the key that matched cannot be inferred from timing. Every rejection produces the same
safe 401 envelope: a caller cannot distinguish a missing header, a wrong value, an
unconfigured credential or a rotation window. Internally, a bounded reason is logged
with the request ID; neither the presented value nor the body is ever recorded.

A previous key alone never authenticates a request: fail closed if no current key is
configured.
"""

from __future__ import annotations

import logging
from hmac import compare_digest
from typing import Final, NoReturn

from fastapi import HTTPException, Request

from thehouse_genai.api.request_context import get_request_id
from thehouse_genai.application.metrics_port import (
    AuthRejectionReason,
    MetricName,
    MetricsRecorder,
)
from thehouse_genai.infrastructure.config import Settings

logger = logging.getLogger(__name__)

_SERVICE_KEY_HEADER: Final = "x-service-key"
_REASON_MISSING_KEY: Final = "missing_key"
_REASON_INVALID_KEY: Final = "invalid_key"
_REASON_NOT_CONFIGURED: Final = "not_configured"


def _matches_configured_key(presented: str, settings: Settings) -> bool:
    """Compare the presented key against every configured key without shortcuts.

    `|=` evaluates both operands, so the previous key is compared even when the current
    one already matched. The comparison work is therefore independent of which key the
    caller presented.
    """

    candidate = presented.encode("utf-8")
    configured = (settings.service_key, settings.service_key_previous)
    matches = False
    for key in configured:
        if key is not None:
            matches |= compare_digest(candidate, key.get_secret_value().encode("utf-8"))
    return matches


def _reject(request: Request, reason: str) -> NoReturn:
    """Log a bounded reason and raise the unchanged 401 envelope."""

    metrics: MetricsRecorder = request.app.state.metrics
    metrics.increment(MetricName.AUTH_REJECTIONS_TOTAL, reason=AuthRejectionReason(reason))
    logger.warning(
        "auth.rejected",
        extra={"request_id": get_request_id(request), "reason": reason},
    )
    raise HTTPException(status_code=401)


def require_service_key(request: Request) -> None:
    """Reject requests without the current or the previous `X-Service-Key`.

    Raises:
        HTTPException: 401 with the standard error envelope on any rejection.
    """

    settings: Settings = request.app.state.settings
    current = settings.service_key
    presented = request.headers.get(_SERVICE_KEY_HEADER)
    if current is None:
        _reject(request, _REASON_NOT_CONFIGURED)
    if presented is None:
        _reject(request, _REASON_MISSING_KEY)
    if not _matches_configured_key(presented, settings):
        _reject(request, _REASON_INVALID_KEY)
