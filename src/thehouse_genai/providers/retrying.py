"""One bounded retry around the provider port.

Only transient vendor failures are retried: an unavailable provider or a rate limit.
Authentication errors, invalid responses and timeouts are never retried, because a
second call cannot fix them and only adds latency and cost. The retry is applied by
the factory, so every use case behind the port (explain-match and parse-search)
gets the same behaviour without knowing about it.

The sleep and the clock are injected: tests are deterministic and never wait for the
real 300 ms. The factory wraps this decorator with `GuardedProvider`, so the whole
sequence is also bounded by `GENAI_TIMEOUT_SECONDS`; the decorator's own total bound
is a second barrier for callers that use it directly.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Final

from thehouse_genai.application.budget_port import DailyBudgetPort
from thehouse_genai.providers.base import (
    GenerativeAiProvider,
    GenerativeAiRequest,
    GenerativeAiResponse,
    ProviderRateLimitError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

DEFAULT_RETRY_DELAY_SECONDS: Final[float] = 0.3
DEFAULT_FIRST_ATTEMPT_LIMIT_SECONDS: Final[float] = 2.5
DEADLINE_MARGIN_SECONDS: Final[float] = 1.0

_RETRY_ATTEMPT: Final[int] = 2

type _Sleep = Callable[[float], Awaitable[None]]
type _Clock = Callable[[], float]


async def _default_sleep(delay: float) -> None:
    """Wait before the retry in production; tests inject a recording double."""

    await asyncio.sleep(delay)


class RetryingProvider:
    """Retry one transient provider failure once, within a caller deadline."""

    def __init__(
        self,
        provider: GenerativeAiProvider,
        *,
        max_total_seconds: float,
        budget: DailyBudgetPort | None = None,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
        first_attempt_limit_seconds: float = DEFAULT_FIRST_ATTEMPT_LIMIT_SECONDS,
        sleep: _Sleep = _default_sleep,
        clock: _Clock = monotonic,
    ) -> None:
        """Bind the delegate and the bounded retry policy.

        Raises:
            ValueError: if the delay is negative or a deadline is not positive.
        """

        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must not be negative")
        if first_attempt_limit_seconds <= 0:
            raise ValueError("first_attempt_limit_seconds must be greater than 0")
        if max_total_seconds <= 0:
            raise ValueError("max_total_seconds must be greater than 0")
        self._provider = provider
        self._budget = budget
        self._max_total_seconds = max_total_seconds
        self._retry_delay_seconds = retry_delay_seconds
        self._first_attempt_limit_seconds = first_attempt_limit_seconds
        self._sleep = sleep
        self._clock = clock

    @property
    def max_total_seconds(self) -> float:
        """Return the total-time bound used to decide whether a retry fits."""

        return self._max_total_seconds

    async def generate(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        """Return the first answer, or retry once if the failure is transient.

        Raises:
            ProviderError: the last normalized failure, when no retry is allowed.
        """

        started = self._clock()
        try:
            return await self._provider.generate(request)
        except (ProviderUnavailableError, ProviderRateLimitError) as exc:
            # A slow failure is not the transient blip this policy is meant for, and
            # a retry must fit both the fixed delay and the caller's total deadline.
            elapsed = self._clock() - started
            if elapsed >= self._first_attempt_limit_seconds:
                raise
            if elapsed + self._retry_delay_seconds >= self._max_total_seconds:
                raise
            if self._budget is not None and not self._budget.reserve_call():
                raise
            await self._sleep(self._retry_delay_seconds)
            if self._clock() - started >= self._max_total_seconds:
                raise
            logger.warning(
                "provider.call.retry",
                extra={"attempt": _RETRY_ATTEMPT, "error_code": exc.code},
            )
            return await self._provider.generate(request)
