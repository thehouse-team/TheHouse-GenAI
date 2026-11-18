"""Daily provider budget tests: offline clocks, exact cost and bounded concurrency."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from thehouse_genai.api.app import create_app
from thehouse_genai.application.budget_port import DailyBudgetPort
from thehouse_genai.application.explain_match import ExplainMatch
from thehouse_genai.application.metrics_port import MetricName, MetricsRecorder
from thehouse_genai.domain.match_explanation import ExplainMatchRequest
from thehouse_genai.infrastructure.budget import DailyBudget
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.infrastructure.metrics import MetricsRegistry
from thehouse_genai.providers.base import GenerativeAiUsage, ProviderTimeoutError
from thehouse_genai.providers.fake import FakeProvider

SERVICE_KEY = "test-service-key"
URL = "/api/v1/generative/explain-match"
_EXPLANATION = "Coincidencia del 87% con tus preferencias."
_NOW = datetime(2026, 11, 18, 23, 59, tzinfo=UTC)


def _payload() -> dict[str, Any]:
    return {
        "matchScore": 87,
        "university": "UTTT",
        "property": {
            "title": "Cuarto cerca de UTTT",
            "price": 2800,
            "currency": "MXN",
            "distanceKm": 1.2,
            "services": ["internet"],
        },
        "preferences": {
            "budgetMax": 3000,
            "currency": "MXN",
            "maxDistanceKm": 2.0,
            "essentialServices": ["internet"],
        },
    }


def _request() -> ExplainMatchRequest:
    return ExplainMatchRequest.model_validate(_payload())


def _completion() -> str:
    return json.dumps({"explanation": _EXPLANATION}, ensure_ascii=False)


def _count(recorder: MetricsRecorder, name: str, **labels: str) -> int:
    for counter in recorder.snapshot().counters:
        if counter.name == name and dict(counter.labels) == labels:
            return counter.value
    return 0


def _budget(
    *,
    enabled: bool = True,
    call_limit: int = 400,
    input_token_limit: int | None = None,
    output_token_limit: int | None = None,
    clock: Callable[[], datetime] | None = None,
) -> DailyBudget:
    return DailyBudget(
        enabled=enabled,
        call_limit=call_limit,
        input_token_limit=input_token_limit,
        output_token_limit=output_token_limit,
        cost_input_per_million=Decimal("0"),
        cost_output_per_million=Decimal("0"),
        clock=clock if clock is not None else lambda: _NOW,
    )


def test_settings_defaults_keep_the_budget_off() -> None:
    settings = Settings(_env_file=None)

    assert settings.budget_enabled is False
    assert settings.daily_call_limit == 400
    assert settings.daily_input_token_limit is None
    assert settings.daily_output_token_limit is None
    assert settings.cost_input_per_million == Decimal("0")
    assert settings.cost_output_per_million == Decimal("0")


def test_settings_read_the_new_environment_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENAI_BUDGET_ENABLED", "true")
    monkeypatch.setenv("GENAI_DAILY_CALL_LIMIT", "7")
    monkeypatch.setenv("GENAI_DAILY_INPUT_TOKEN_LIMIT", "10")
    monkeypatch.setenv("GENAI_DAILY_OUTPUT_TOKEN_LIMIT", "20")
    monkeypatch.setenv("GENAI_COST_INPUT_PER_MILLION", "1.5")
    monkeypatch.setenv("GENAI_COST_OUTPUT_PER_MILLION", "2.5")

    settings = Settings(_env_file=None)

    assert settings.budget_enabled is True
    assert settings.daily_call_limit == 7
    assert settings.daily_input_token_limit == 10
    assert settings.daily_output_token_limit == 20
    assert settings.cost_input_per_million == Decimal("1.5")
    assert settings.cost_output_per_million == Decimal("2.5")


def test_settings_accept_explicit_aliased_kwargs() -> None:
    settings = Settings(
        _env_file=None,
        budget_enabled=True,
        daily_call_limit=9,
        daily_input_token_limit=11,
        daily_output_token_limit=13,
        cost_input_per_million=Decimal("3.5"),
    )

    assert settings.daily_call_limit == 9
    assert settings.daily_input_token_limit == 11
    assert settings.daily_output_token_limit == 13
    assert settings.cost_input_per_million == Decimal("3.5")


def test_disabled_budget_never_blocks_or_reports_exhaustion() -> None:
    budget = _budget(enabled=False, call_limit=1)

    assert budget.reserve_call() is True
    assert budget.reserve_call() is True

    snapshot = budget.snapshot()
    assert snapshot.exhausted is False
    assert snapshot.calls_used == 2
    assert isinstance(budget, DailyBudgetPort)


def test_successful_calls_consume_slots_and_record_tokens() -> None:
    budget = _budget(call_limit=2)
    registry = MetricsRegistry()
    provider = FakeProvider(
        text=_completion(),
        usage=GenerativeAiUsage(input_tokens=11, output_tokens=7),
    )
    use_case = ExplainMatch(provider, metrics=registry, budget=budget)

    first = asyncio.run(use_case.execute(_request()))
    second = asyncio.run(use_case.execute(_request()))

    assert first.generated is True
    assert second.generated is True
    snapshot = budget.snapshot()
    assert snapshot.calls_used == 2
    assert snapshot.input_tokens_used == 22
    assert snapshot.output_tokens_used == 14
    assert _count(registry, MetricName.PROVIDER_CALLS_TOTAL, outcome="success") == 2


def test_failed_call_consumes_a_slot_but_no_tokens() -> None:
    budget = _budget(call_limit=2)
    provider = FakeProvider(error=ProviderTimeoutError())
    use_case = ExplainMatch(provider, budget=budget)

    first = asyncio.run(use_case.execute(_request()))
    second = asyncio.run(use_case.execute(_request()))

    assert first.generated is False
    assert second.generated is False
    assert len(provider.calls) == 2
    snapshot = budget.snapshot()
    assert snapshot.calls_used == 2
    assert snapshot.input_tokens_used == 0
    assert snapshot.output_tokens_used == 0


def test_exhausted_budget_returns_a_fallback_without_calling_gemini() -> None:
    settings = Settings(
        app_env="test",
        service_key=SERVICE_KEY,
        genai_provider="fake",
        budget_enabled=True,
        daily_call_limit=1,
        _env_file=None,
    )
    app = create_app(settings)
    provider = FakeProvider(text=_completion())
    app.state.provider = provider

    with TestClient(app) as client:
        first = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        second = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert first.status_code == 200
    assert first.json()["generated"] is True
    assert second.status_code == 200
    assert set(second.json()) == set(first.json())
    assert second.json()["generated"] is False
    assert second.json()["promptVersion"] == first.json()["promptVersion"]
    assert len(provider.calls) == 1
    assert _count(app.state.metrics, MetricName.BUDGET_EXHAUSTIONS_TOTAL) == 1
    reason = "BUDGET_EXHAUSTED"
    assert _count(app.state.metrics, MetricName.EXPLAIN_MATCH_FALLBACKS_TOTAL, reason=reason) == 1


def test_midnight_rollover_resets_counters_with_a_fake_clock() -> None:
    clock = {"now": _NOW}
    budget = _budget(call_limit=1, clock=lambda: clock["now"])

    assert budget.reserve_call() is True
    assert budget.reserve_call() is False
    first = budget.snapshot()
    assert first.day == "2026-11-18"
    assert first.resets_at == "2026-11-19T00:00:00-06:00"

    clock["now"] = datetime(2026, 11, 19, 6, 1, tzinfo=UTC)

    assert budget.reserve_call() is True
    second = budget.snapshot()
    assert second.day == "2026-11-19"
    assert second.calls_used == 1
    assert second.resets_at == "2026-11-20T00:00:00-06:00"


def test_token_limit_blocks_the_following_call() -> None:
    budget = _budget(call_limit=10, input_token_limit=10)
    registry = MetricsRegistry()
    provider = FakeProvider(
        text=_completion(),
        usage=GenerativeAiUsage(input_tokens=11, output_tokens=0),
    )
    use_case = ExplainMatch(provider, metrics=registry, budget=budget)

    first = asyncio.run(use_case.execute(_request()))
    second = asyncio.run(use_case.execute(_request()))

    assert first.generated is True
    assert second.generated is False
    assert len(provider.calls) == 1
    assert budget.snapshot().exhausted is True
    reason = "BUDGET_EXHAUSTED"
    assert _count(registry, MetricName.EXPLAIN_MATCH_FALLBACKS_TOTAL, reason=reason) == 1


def test_cost_is_exact_decimal_and_exposed_as_a_string_gauge() -> None:
    budget = DailyBudget(
        enabled=False,
        call_limit=400,
        input_token_limit=None,
        output_token_limit=None,
        cost_input_per_million=Decimal("100"),
        cost_output_per_million=Decimal("200"),
        clock=lambda: _NOW,
    )
    registry = MetricsRegistry()
    provider = FakeProvider(
        text=_completion(),
        usage=GenerativeAiUsage(input_tokens=11, output_tokens=7),
    )
    use_case = ExplainMatch(provider, metrics=registry, budget=budget)

    asyncio.run(use_case.execute(_request()))
    asyncio.run(use_case.execute(_request()))

    assert budget.snapshot().estimated_cost == "0.005"
    gauges = [
        gauge for gauge in registry.snapshot().gauges if gauge.name == "provider_estimated_cost"
    ]
    assert len(gauges) == 1
    assert gauges[0].value == "0.005"
    assert registry.snapshot().to_json().count('"value": "0.005"') == 1


def test_concurrent_reservations_never_exceed_the_limit() -> None:
    budget = _budget(call_limit=5)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _index: budget.reserve_call(), range(50)))

    assert sum(results) == 5
    snapshot = budget.snapshot()
    assert snapshot.calls_used == 5
    assert snapshot.exhausted is True


def test_budget_snapshot_serializes_with_the_cost_as_a_string() -> None:
    data = _budget().snapshot().to_dict()

    assert data["enabled"] is True
    assert data["call_limit"] == 400
    assert data["input_token_limit"] is None
    assert data["estimated_cost"] == "0"
