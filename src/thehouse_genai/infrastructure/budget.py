"""Process-local daily provider budget with a fixed UTC-6 local day.

The clock is wall-clock (not monotonic) because the window resets at local midnight.
Limits are checked and consumed under a short lock; the lock is never held across an
await. State is per process and disappears on restart: see spec 007, appendix C.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Final

from thehouse_genai.application.budget_port import (
    LOCAL_UTC_OFFSET_HOURS,
    TOKENS_PER_MILLION,
    BudgetSnapshot,
    DailyBudgetPort,
)

_LOCAL_TZ: Final[timezone] = timezone(timedelta(hours=LOCAL_UTC_OFFSET_HOURS))


class DailyBudget:
    """Consume one call at a time and account for the tokens actually reported."""

    def __init__(
        self,
        *,
        enabled: bool,
        call_limit: int,
        input_token_limit: int | None,
        output_token_limit: int | None,
        cost_input_per_million: Decimal,
        cost_output_per_million: Decimal,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Bind limits, rates and an injectable wall clock for deterministic tests."""

        if call_limit < 1:
            raise ValueError("call_limit must be at least 1")
        if input_token_limit is not None and input_token_limit < 0:
            raise ValueError("input_token_limit must not be negative")
        if output_token_limit is not None and output_token_limit < 0:
            raise ValueError("output_token_limit must not be negative")
        if cost_input_per_million < 0 or cost_output_per_million < 0:
            raise ValueError("cost rates must not be negative")
        self._enabled = enabled
        self._call_limit = call_limit
        self._input_limit = input_token_limit
        self._output_limit = output_token_limit
        self._cost_in = cost_input_per_million
        self._cost_out = cost_output_per_million
        self._clock = clock if clock is not None else lambda: datetime.now(UTC)
        self._lock = threading.Lock()
        self._day = self._local_day()
        self._calls = 0
        self._input_tokens = 0
        self._output_tokens = 0

    def reserve_call(self) -> bool:
        """Atomically check the daily limits and consume one call slot."""

        with self._lock:
            self._rollover_locked()
            would_exceed = (
                self._calls + 1 > self._call_limit
                or (self._input_limit is not None and self._input_tokens >= self._input_limit)
                or (self._output_limit is not None and self._output_tokens >= self._output_limit)
            )
            if self._enabled and would_exceed:
                return False
            self._calls += 1
            return True

    def record_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Add the usage reported by a successful provider call."""

        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token counts must not be negative")
        with self._lock:
            self._rollover_locked()
            self._input_tokens += input_tokens
            self._output_tokens += output_tokens

    def snapshot(self) -> BudgetSnapshot:
        """Return an immutable view of the current local day."""

        with self._lock:
            self._rollover_locked()
            exhausted = self._exhausted_locked()
            cost = self._cost_locked()
            return BudgetSnapshot(
                enabled=self._enabled,
                exhausted=exhausted,
                day=self._day,
                resets_at=self._reset_time_locked(),
                calls_used=self._calls,
                call_limit=self._call_limit,
                input_tokens_used=self._input_tokens,
                input_token_limit=self._input_limit,
                output_tokens_used=self._output_tokens,
                output_token_limit=self._output_limit,
                estimated_cost=str(cost),
            )

    def _local_now(self) -> datetime:
        """Return the injected instant in the fixed local timezone."""

        value = self._clock()
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(_LOCAL_TZ)

    def _local_day(self) -> str:
        return self._local_now().date().isoformat()

    def _rollover_locked(self) -> None:
        """Reset the counters when the local day changes."""

        day = self._local_day()
        if day != self._day:
            self._day = day
            self._calls = 0
            self._input_tokens = 0
            self._output_tokens = 0

    def _reset_time_locked(self) -> str:
        """Return the next local midnight as an ISO timestamp."""

        tomorrow = self._local_now().date() + timedelta(days=1)
        return datetime.combine(tomorrow, time.min, tzinfo=_LOCAL_TZ).isoformat()

    def _exhausted_locked(self) -> bool:
        if not self._enabled:
            return False
        if self._calls >= self._call_limit:
            return True
        if self._input_limit is not None and self._input_tokens >= self._input_limit:
            return True
        return bool(self._output_limit is not None and self._output_tokens >= self._output_limit)

    def _cost_locked(self) -> Decimal:
        """Compute the cumulative cost from exact token counts and configured rates."""

        numerator = (
            Decimal(self._input_tokens) * self._cost_in
            + Decimal(self._output_tokens) * self._cost_out
        )
        return numerator / Decimal(TOKENS_PER_MILLION)


_BUDGET: Final[type[DailyBudgetPort]] = DailyBudget
