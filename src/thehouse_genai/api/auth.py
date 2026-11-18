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
from pydantic import SecretStr

from thehouse_genai.api.request_context import get_request_id
from thehouse_genai.application.metrics_port import (
    AuthRejectionReason,
    MetricName,
    MetricsRecorder,
)
from thehouse_genai.infrastructure.config import Settings

logger = logging.getLogger(__name__)

_SERVICE_KEY_HEADER: Final = "x-service-key"
_METRICS_KEY_HEADER: Final = "x-metrics-key"
_REASON_MISSING_KEY: Final = "missing_key"
_REASON_INVALID_KEY: Final = "invalid_key"
_REASON_NOT_CONFIGURED: Final = "not_configured"


def matches_any_key(presented: str, configured: tuple[SecretStr | None, ...]) -> bool:
    """Compare a presented key against every configured key without shortcuts.

    `|=` evaluates both operands, so every configured key is compared even after a match.
    The work is therefore independent of which key the caller presented.
    """

    candidate = presented.encode("utf-8")
    matches = False
    for key in configured:
        if key is not None:
            matches |= compare_digest(candidate, key.get_secret_value().encode("utf-8"))
    return matches


def _matches_configured_key(presented: str, settings: Settings) -> bool:
    """Compare against the service keys, including the outgoing rotation key."""

    return matches_any_key(presented, (settings.service_key, settings.service_key_previous))


def _reject(
    request: Request,
    reason: str,
    *,
    metric: MetricName = MetricName.AUTH_REJECTIONS_TOTAL,
    event: str = "auth.rejected",
) -> NoReturn:
    """Log a bounded reason and raise the unchanged 401 envelope."""

    metrics: MetricsRecorder = request.app.state.metrics
    metrics.increment(metric, reason=AuthRejectionReason(reason))
    logger.warning(
        event,
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


def require_metrics_key(request: Request) -> None:
    """Protect internal diagnostics with the separate `X-Metrics-Key` credential.

    The service key never opens these endpoints and this key never opens generative
    endpoints. Fail closed when no metrics key is configured.
    """

    settings: Settings = request.app.state.settings
    configured = settings.metrics_key
    presented = request.headers.get(_METRICS_KEY_HEADER)
    if configured is None:
        _reject(
            request,
            _REASON_NOT_CONFIGURED,
            metric=MetricName.METRICS_AUTH_REJECTIONS_TOTAL,
            event="metrics_auth.rejected",
        )
    if presented is None:
        _reject(
            request,
            _REASON_MISSING_KEY,
            metric=MetricName.METRICS_AUTH_REJECTIONS_TOTAL,
            event="metrics_auth.rejected",
        )
    if not matches_any_key(presented, (configured,)):
        _reject(
            request,
            _REASON_INVALID_KEY,
            metric=MetricName.METRICS_AUTH_REJECTIONS_TOTAL,
            event="metrics_auth.rejected",
        )
