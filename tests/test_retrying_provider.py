"""Bounded retry tests: offline doubles and a Gemini mock transport only.

No test waits for the real delay or reaches the vendor: the sleep, the clock and
the HTTP client are all injected.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from decimal import Decimal
from time import monotonic
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from thehouse_genai.application.explain_match import ExplainMatch
from thehouse_genai.domain.match_explanation import ExplainMatchRequest
from thehouse_genai.infrastructure.budget import DailyBudget
from thehouse_genai.providers.base import (
    GenerativeAiProvider,
    GenerativeAiRequest,
    GenerativeAiResponse,
    GenerativeAiUsage,
    GuardedProvider,
    ProviderError,
    ProviderUnavailableError,
)
from thehouse_genai.providers.gemini import GeminiProvider
from thehouse_genai.providers.retrying import RetryingProvider

KEY = "test-key-not-a-real-credential"
MODEL = "gemini-3.8-flash"
PORT_REQUEST = GenerativeAiRequest(prompt="hola")
_EXPLANATION = "Coincidencia del 87% con tus preferencias."
_SUCCESS_PAYLOAD = {
    "candidates": [
        {
            "content": {"parts": [{"text": json.dumps({"explanation": _EXPLANATION})}]},
            "finishReason": "STOP",
        }
    ],
    "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 7},
    "modelVersion": MODEL,
}


class _SleepRecorder:
    """Record delays instead of waiting."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class _Clock:
    """Return prearranged instants for deterministic deadline checks."""

    def __init__(self, *values: float) -> None:
        self._values = iter(values)

    def __call__(self) -> float:
        return next(self._values)


class _ScriptedProvider:
    """Answer from a fixed sequence and expose the number of attempts."""

    def __init__(self, *outcomes: GenerativeAiResponse | ProviderError) -> None:
        self._outcomes = outcomes
        self.calls = 0

    async def generate(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        del request
        outcome = self._outcomes[min(self.calls, len(self._outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, ProviderError):
            raise outcome
        return outcome


def _response(text: str = _EXPLANATION) -> GenerativeAiResponse:
    """Build a valid port response."""

    return GenerativeAiResponse(
        text=text,
        usage=GenerativeAiUsage(input_tokens=1, output_tokens=1),
    )


def _budget(call_limit: int) -> DailyBudget:
    """Build a real daily budget with an explicit call limit."""

    return DailyBudget(
        enabled=True,
        call_limit=call_limit,
        input_token_limit=None,
        output_token_limit=None,
        cost_input_per_million=Decimal(0),
        cost_output_per_million=Decimal(0),
    )


def _gemini(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    budget: DailyBudget | None = None,
    sleep: _SleepRecorder | None = None,
    clock: _Clock | None = None,
    max_total_seconds: float = 8.0,
) -> RetryingProvider:
    """Wrap a mock-backed Gemini adapter in the retry decorator."""

    return RetryingProvider(
        GeminiProvider(
            api_key=SecretStr(KEY),
            model=MODEL,
            timeout_seconds=1.0,
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ),
        budget=budget,
        max_total_seconds=max_total_seconds,
        sleep=sleep or _SleepRecorder(),
        clock=clock or monotonic,
    )


def _guarded(provider: GenerativeAiProvider) -> GuardedProvider:
    """Apply the same guard the factory applies in production."""

    return GuardedProvider(
        provider,
        timeout_seconds=2.0,
        max_input_chars=4_000,
    )


def _request() -> ExplainMatchRequest:
    """Build a valid explain-match request."""

    payload: dict[str, Any] = {
        "matchScore": 87,
        "university": "UTTT",
        "property": {
            "title": "Cuarto cerca de UTTT",
            "price": Decimal("2800"),
            "currency": "MXN",
            "distanceKm": 1.2,
            "services": ["internet"],
        },
        "preferences": {
            "budgetMax": Decimal("3000"),
            "currency": "MXN",
            "maxDistanceKm": 2.0,
            "essentialServices": ["internet"],
        },
    }
    return ExplainMatchRequest.model_validate(payload)


def test_unavailable_then_success_generates_with_two_calls() -> None:
    seen: list[httpx.Request] = []
    sleep = _SleepRecorder()

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(503, json={"error": "transient"})
        return httpx.Response(200, json=_SUCCESS_PAYLOAD)

    use_case = ExplainMatch(_guarded(_gemini(_respond, sleep=sleep)))

    response = asyncio.run(use_case.execute(_request()))

    assert response.generated is True
    assert response.explanation == _EXPLANATION
    assert len(seen) == 2
    assert sleep.delays == [0.3]


def test_rate_limit_is_not_retried() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(429, json={"error": "per-minute quota exhausted"})

    response = asyncio.run(ExplainMatch(_guarded(_gemini(_respond))).execute(_request()))

    assert response.generated is False
    assert len(seen) == 1


def test_persistent_unavailable_degrades_after_two_calls(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(503, json={"error": "still down"})

    response = asyncio.run(ExplainMatch(_guarded(_gemini(_respond))).execute(_request()))

    assert response.generated is False
    assert caplog.records[-1].fallback_reason == "PROVIDER_ERROR"
    assert len(seen) == 2


def test_auth_error_is_not_retried() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(401, json={"error": "invalid key"})

    response = asyncio.run(ExplainMatch(_guarded(_gemini(_respond))).execute(_request()))

    assert response.generated is False
    assert len(seen) == 1


def test_timeout_is_not_retried() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        raise httpx.ReadTimeout("vendor timeout")

    response = asyncio.run(ExplainMatch(_guarded(_gemini(_respond))).execute(_request()))

    assert response.generated is False
    assert len(seen) == 1


def test_invalid_response_is_not_retried() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"candidates": []})

    response = asyncio.run(ExplainMatch(_guarded(_gemini(_respond))).execute(_request()))

    assert response.generated is False
    assert len(seen) == 1


def test_slow_first_attempt_is_not_retried() -> None:
    sleep = _SleepRecorder()
    delegate = _ScriptedProvider(ProviderUnavailableError(), _response())
    provider = RetryingProvider(
        delegate,
        max_total_seconds=8.0,
        sleep=sleep,
        clock=_Clock(0.0, 2.6),
    )

    with pytest.raises(ProviderUnavailableError):
        asyncio.run(provider.generate(PORT_REQUEST))

    assert delegate.calls == 1
    assert sleep.delays == []


def test_retry_must_fit_the_total_deadline() -> None:
    sleep = _SleepRecorder()
    delegate = _ScriptedProvider(ProviderUnavailableError(), _response())
    provider = RetryingProvider(
        delegate,
        max_total_seconds=1.0,
        sleep=sleep,
        clock=_Clock(0.0, 0.5, 1.1),
    )

    with pytest.raises(ProviderUnavailableError):
        asyncio.run(provider.generate(PORT_REQUEST))

    assert delegate.calls == 1
    assert sleep.delays == [0.3]


def test_expired_deadline_after_sleep_does_not_reserve_budget() -> None:
    sleep = _SleepRecorder()
    budget = _budget(call_limit=5)
    delegate = _ScriptedProvider(ProviderUnavailableError(), _response())
    provider = RetryingProvider(
        delegate,
        budget=budget,
        max_total_seconds=1.0,
        sleep=sleep,
        clock=_Clock(0.0, 0.5, 1.1),
    )
    before = budget.snapshot().calls_used

    with pytest.raises(ProviderUnavailableError):
        asyncio.run(provider.generate(PORT_REQUEST))

    assert budget.snapshot().calls_used == before
    assert delegate.calls == 1
    assert sleep.delays == [0.3]


def test_each_attempt_reserves_the_daily_budget() -> None:
    seen: list[httpx.Request] = []
    budget = _budget(call_limit=3)

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(503, json={"error": "transient"})
        return httpx.Response(200, json=_SUCCESS_PAYLOAD)

    use_case = ExplainMatch(_guarded(_gemini(_respond, budget=budget)), budget=budget)

    response = asyncio.run(use_case.execute(_request()))

    assert response.generated is True
    assert budget.snapshot().calls_used == 2
    assert len(seen) == 2


def test_no_budget_left_prevents_the_retry() -> None:
    seen: list[httpx.Request] = []
    sleep = _SleepRecorder()
    budget = _budget(call_limit=1)  # the use case consumes the only slot

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(503, json={"error": "transient"})

    use_case = ExplainMatch(_guarded(_gemini(_respond, budget=budget, sleep=sleep)), budget=budget)

    response = asyncio.run(use_case.execute(_request()))

    assert response.generated is False
    assert len(seen) == 1
    assert sleep.delays == [0.3]  # the delay precedes the budget check
    assert budget.snapshot().calls_used == 1


def test_retry_log_records_attempt_and_error_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    provider = RetryingProvider(
        _ScriptedProvider(ProviderUnavailableError(), _response()),
        max_total_seconds=8.0,
        sleep=_SleepRecorder(),
    )

    asyncio.run(provider.generate(PORT_REQUEST))

    retries = [r for r in caplog.records if r.getMessage() == "provider.call.retry"]
    assert len(retries) == 1
    assert retries[0].attempt == 2
    assert retries[0].error_code == "PROVIDER_UNAVAILABLE"


def test_negative_delay_is_rejected() -> None:
    with pytest.raises(ValueError, match="retry_delay_seconds"):
        RetryingProvider(
            _ScriptedProvider(_response()),
            max_total_seconds=8.0,
            retry_delay_seconds=-0.1,
        )
