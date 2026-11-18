"""Port and immutable view for the process-local daily provider budget.

The application layer owns the contract so the use case never imports infrastructure.
All monetary values cross the boundary as strings holding an exact ``Decimal``; no
credential, prompt or response content is part of this port.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol, runtime_checkable

LOCAL_UTC_OFFSET_HOURS: Final[int] = -6
TOKENS_PER_MILLION: Final[int] = 1_000_000


@dataclass(frozen=True)
class BudgetSnapshot:
    """A stable, JSON-ready view of the budget at one instant."""

    enabled: bool
    exhausted: bool
    day: str
    resets_at: str
    calls_used: int
    call_limit: int
    input_tokens_used: int
    input_token_limit: int | None
    output_tokens_used: int
    output_token_limit: int | None
    estimated_cost: str

    def to_dict(self) -> dict[str, object]:
        """Return a fresh plain dict with the cost kept as an exact string."""

        return {
            "enabled": self.enabled,
            "exhausted": self.exhausted,
            "day": self.day,
            "resets_at": self.resets_at,
            "calls_used": self.calls_used,
            "call_limit": self.call_limit,
            "input_tokens_used": self.input_tokens_used,
            "input_token_limit": self.input_token_limit,
            "output_tokens_used": self.output_tokens_used,
            "output_token_limit": self.output_token_limit,
            "estimated_cost": self.estimated_cost,
        }


@runtime_checkable
class DailyBudgetPort(Protocol):
    """Reserve provider calls and account for their reported token usage."""

    def reserve_call(self) -> bool:
        """Atomically check the daily limits and consume one call slot."""

    def record_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Add the usage reported by a successful provider call."""

    def snapshot(self) -> BudgetSnapshot:
        """Return an immutable view of the current local day."""
