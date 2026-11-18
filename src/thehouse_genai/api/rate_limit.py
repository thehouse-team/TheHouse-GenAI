"""Process-local fixed-window rate limiting for generative endpoints.

The client identity is a fingerprint of the presented service key: no IP address or
client-supplied header is trusted. The state lives in this process only; see spec 005
for the multi-instance limitation. Authentication runs before this guard, so a request
without a valid key never consumes anyone's budget.
"""

from __future__ import annotations

import logging
import math
import threading
from collections.abc import Callable
from time import monotonic
from typing import Final

from fastapi import HTTPException, Request

from thehouse_genai.api.request_context import get_request_id
from thehouse_genai.application.metrics_port import MetricName, MetricsRecorder
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.infrastructure.redaction import fingerprint

logger = logging.getLogger(__name__)

_SERVICE_KEY_HEADER: Final = "x-service-key"


class InMemoryRateLimiter:
    """Fixed-window counters keyed by client fingerprint, scoped to one process."""

    def __init__(
        self,
        *,
        requests: int,
        window_seconds: int,
        max_clients: int,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Bind the budget and an injectable monotonic clock for deterministic tests."""

        if requests <= 0 or window_seconds <= 0 or max_clients <= 0:
            raise ValueError("rate limit settings must be greater than 0")
        self._requests = requests
        self._window_seconds = window_seconds
        self._max_clients = max_clients
        self._clock = clock if clock is not None else monotonic
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[int, float]] = {}

    def check(self, client_id: str) -> tuple[bool, int]:
        """Consume one slot and report whether it was allowed and the retry delay."""

        now = self._clock()
        with self._lock:
            entry = self._windows.get(client_id)
            if entry is None or now - entry[1] >= self._window_seconds:
                self._windows[client_id] = (1, now)
                self._prune(now)
                return True, 0
            count, started = entry
            if count < self._requests:
                self._windows[client_id] = (count + 1, started)
                return True, 0
            retry_after = max(1, math.ceil(self._window_seconds - (now - started)))
            return False, retry_after

    @property
    def tracked_clients(self) -> tuple[str, ...]:
        """Return the tracked fingerprints for test assertions, never the keys."""

        with self._lock:
            return tuple(self._windows)

    def _prune(self, now: float) -> None:
        """Drop expired windows, then the oldest ones if the client cap is exceeded."""

        if len(self._windows) <= self._max_clients:
            return
        for client_id, (_, started) in list(self._windows.items()):
            if now - started >= self._window_seconds:
                del self._windows[client_id]
        while len(self._windows) > self._max_clients:
            oldest = min(self._windows, key=lambda client_id: self._windows[client_id][1])
            del self._windows[oldest]


async def enforce_rate_limit(request: Request) -> None:
    """Reject requests that exceed the process-local client budget.

    Raises:
        HTTPException: 429 with `Retry-After` when the window is exhausted.
    """

    settings: Settings = request.app.state.settings
    if not settings.rate_limit_enabled:
        return
    presented = request.headers.get(_SERVICE_KEY_HEADER)
    if presented is None:
        return
    limiter: InMemoryRateLimiter = request.app.state.rate_limiter
    client_id = fingerprint(presented)
    allowed, retry_after = limiter.check(client_id)
    if allowed:
        return
    metrics: MetricsRecorder = request.app.state.metrics
    metrics.increment(MetricName.RATE_LIMIT_REJECTIONS_TOTAL)
    logger.warning(
        "rate_limit.rejected",
        extra={
            "request_id": get_request_id(request),
            "reason": "limit_exceeded",
            "client_id": client_id,
            "retry_after_seconds": retry_after,
        },
    )
    raise HTTPException(status_code=429, headers={"Retry-After": str(retry_after)})
