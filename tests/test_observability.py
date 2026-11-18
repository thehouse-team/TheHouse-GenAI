"""Application metrics and request-id correlation tests.

Providers are offline doubles or a Gemini adapter backed by a `MockTransport`: the suite
never opens a socket and never reads a real credential.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from thehouse_genai.api.app import create_app
from thehouse_genai.api.request_context import request_id_ctx
from thehouse_genai.application.explain_match import ExplainMatch
from thehouse_genai.application.metrics_port import (
    AuthRejectionReason,
    MetricName,
    MetricsRecorder,
)
from thehouse_genai.domain.match_explanation import ExplainMatchRequest
from thehouse_genai.domain.moderation import ModerationDecision, ModerationReason
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.infrastructure.logging import RequestIdFilter
from thehouse_genai.infrastructure.metrics import MetricsRegistry
from thehouse_genai.providers.base import (
    GenerativeAiUsage,
    GuardedProvider,
    ProviderTimeoutError,
)
from thehouse_genai.providers.fake import FakeProvider
from thehouse_genai.providers.gemini import GeminiProvider
from thehouse_genai.providers.moderation import (
    FakeModerationProvider,
    LocalRuleModerator,
    ModerationUnavailableError,
)

SERVICE_KEY = "test-service-key"
GEMINI_KEY = "test-key-not-a-real-credential"
URL = "/api/v1/generative/explain-match"
_EXPLANATION = "Coincidencia del 87% con tus preferencias."


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


def _capture(caplog: pytest.LogCaptureFixture) -> None:
    """Re-attach caplog's handler after create_app clears the root handlers."""

    root = logging.getLogger()
    if caplog.handler not in root.handlers:
        root.addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG)


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "service_key": SERVICE_KEY,
        "genai_provider": "fake",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _gemini_app() -> tuple[FastAPI, list[httpx.Request]]:
    """Build an app whose provider is a Gemini adapter backed by a mock transport."""

    seen: list[httpx.Request] = []
    payload = {
        "candidates": [
            {"content": {"parts": [{"text": _completion()}]}, "finishReason": "STOP"}
        ],
        "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 7},
        "modelVersion": "gemini-3.8-flash-2026-01-01",
    }

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=payload)

    provider = GuardedProvider(
        GeminiProvider(
            api_key=SecretStr(GEMINI_KEY),
            model="gemini-3.8-flash",
            timeout_seconds=1.0,
            client=httpx.AsyncClient(transport=httpx.MockTransport(_respond)),
        ),
        timeout_seconds=1.0,
        max_input_chars=4_000,
    )
    app = create_app(_settings())
    app.state.provider = provider
    return app, seen


def test_success_records_provider_tokens_and_outcome() -> None:
    registry = MetricsRegistry()
    provider = FakeProvider(
        text=_completion(),
        usage=GenerativeAiUsage(input_tokens=11, output_tokens=7),
    )

    response = asyncio.run(ExplainMatch(provider, metrics=registry).execute(_request()))

    assert response.generated is True
    assert _count(registry, MetricName.PROVIDER_CALLS_TOTAL, outcome="success") == 1
    assert _count(registry, MetricName.PROVIDER_TOKENS_TOTAL, direction="input") == 11
    assert _count(registry, MetricName.PROVIDER_TOKENS_TOTAL, direction="output") == 7
    assert _count(registry, MetricName.EXPLAIN_MATCH_OUTCOMES_TOTAL, generated="true") == 1


def test_provider_error_records_taxonomy_code_and_fallback() -> None:
    registry = MetricsRegistry()

    response = asyncio.run(
        ExplainMatch(FakeProvider(error=ProviderTimeoutError()), metrics=registry).execute(
            _request()
        )
    )

    assert response.generated is False
    assert _count(registry, MetricName.PROVIDER_CALLS_TOTAL, outcome="error") == 1
    assert _count(registry, MetricName.PROVIDER_ERRORS_TOTAL, code="PROVIDER_TIMEOUT") == 1
    reason = "PROVIDER_ERROR"
    assert _count(registry, MetricName.EXPLAIN_MATCH_FALLBACKS_TOTAL, reason=reason) == 1
    assert _count(registry, MetricName.EXPLAIN_MATCH_OUTCOMES_TOTAL, generated="false") == 1
    assert _count(registry, MetricName.PROVIDER_TOKENS_TOTAL, direction="input") == 0


def test_invalid_json_is_a_successful_call_with_a_fallback() -> None:
    registry = MetricsRegistry()

    response = asyncio.run(
        ExplainMatch(FakeProvider(text="not json"), metrics=registry).execute(_request())
    )

    assert response.generated is False
    assert _count(registry, MetricName.PROVIDER_CALLS_TOTAL, outcome="success") == 1
    reason = "INVALID_JSON"
    assert _count(registry, MetricName.EXPLAIN_MATCH_FALLBACKS_TOTAL, reason=reason) == 1
    assert _count(registry, MetricName.PROVIDER_ERRORS_TOTAL, code="PROVIDER_TIMEOUT") == 0


def test_no_provider_records_only_the_fallback() -> None:
    registry = MetricsRegistry()

    response = asyncio.run(ExplainMatch(None, metrics=registry).execute(_request()))

    assert response.generated is False
    assert _count(registry, MetricName.EXPLAIN_MATCH_FALLBACKS_TOTAL, reason="NO_PROVIDER") == 1
    names = {counter.name for counter in registry.snapshot().counters}
    assert MetricName.PROVIDER_CALLS_TOTAL not in names


def test_moderation_block_records_decision_and_category() -> None:
    registry = MetricsRegistry()
    moderator = FakeModerationProvider(
        decision=ModerationDecision.BLOCK,
        reasons=(ModerationReason.EMAIL,),
    )
    use_case = ExplainMatch(
        FakeProvider(text=_completion()),
        moderator=moderator,
        metrics=registry,
    )

    response = asyncio.run(use_case.execute(_request()))

    assert response.generated is False
    decision = _count(registry, MetricName.MODERATION_DECISIONS_TOTAL, decision="block")
    assert decision == 1
    assert _count(registry, MetricName.MODERATION_CATEGORIES_TOTAL, category="PII") == 1
    reason = "MODERATION_BLOCKED"
    assert _count(registry, MetricName.EXPLAIN_MATCH_FALLBACKS_TOTAL, reason=reason) == 1


def test_moderation_allow_is_recorded_on_success() -> None:
    registry = MetricsRegistry()
    use_case = ExplainMatch(
        FakeProvider(text=_completion()),
        moderator=LocalRuleModerator(),
        metrics=registry,
    )

    asyncio.run(use_case.execute(_request()))

    decision = _count(registry, MetricName.MODERATION_DECISIONS_TOTAL, decision="allow")
    assert decision == 1
    assert _count(registry, MetricName.MODERATION_CATEGORIES_TOTAL, category="PII") == 0


def test_moderator_error_records_only_the_fallback() -> None:
    registry = MetricsRegistry()
    use_case = ExplainMatch(
        FakeProvider(text=_completion()),
        moderator=FakeModerationProvider(error=ModerationUnavailableError()),
        metrics=registry,
    )

    asyncio.run(use_case.execute(_request()))

    reason = "MODERATION_UNAVAILABLE"
    assert _count(registry, MetricName.EXPLAIN_MATCH_FALLBACKS_TOTAL, reason=reason) == 1
    assert _count(registry, MetricName.MODERATION_DECISIONS_TOTAL, decision="allow") == 0


def test_metrics_recorder_is_optional() -> None:
    response = asyncio.run(ExplainMatch(FakeProvider(text=_completion())).execute(_request()))

    assert response.generated is True


def test_auth_rejection_reasons_are_counted() -> None:
    app = create_app(_settings())

    with TestClient(app) as client:
        assert client.post(URL, json=_payload()).status_code == 401
        wrong = client.post(URL, json=_payload(), headers={"X-Service-Key": "wrong-key"})
        assert wrong.status_code == 401

    expected = AuthRejectionReason.MISSING_KEY.value
    assert _count(app.state.metrics, MetricName.AUTH_REJECTIONS_TOTAL, reason=expected) == 1
    expected = AuthRejectionReason.INVALID_KEY.value
    assert _count(app.state.metrics, MetricName.AUTH_REJECTIONS_TOTAL, reason=expected) == 1


def test_not_configured_rejection_is_counted() -> None:
    settings = Settings(
        app_env="test",
        service_key=None,
        genai_provider="fake",
        _env_file=None,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert response.status_code == 401
    expected = AuthRejectionReason.NOT_CONFIGURED.value
    assert _count(app.state.metrics, MetricName.AUTH_REJECTIONS_TOTAL, reason=expected) == 1


def test_rate_limit_rejection_is_counted() -> None:
    app = create_app(_settings(rate_limit_requests=1))
    app.state.provider = FakeProvider(text=_completion())

    with TestClient(app) as client:
        first = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        response = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert first.status_code == 200
    assert response.status_code == 429
    assert _count(app.state.metrics, MetricName.RATE_LIMIT_REJECTIONS_TOTAL) == 1


def test_request_id_is_correlated_without_reaching_gemini(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app, seen = _gemini_app()
    _capture(caplog)

    with TestClient(app) as client:
        response = client.post(
            URL,
            json=_payload(),
            headers={"X-Service-Key": SERVICE_KEY, "X-Request-ID": "req-observability-7"},
        )

    assert response.status_code == 200
    provider_logs = [r for r in caplog.records if r.getMessage() == "provider.call.completed"]
    use_case_logs = [r for r in caplog.records if r.getMessage() == "explain_match.completed"]
    assert len(provider_logs) == 1
    assert provider_logs[0].request_id == "req-observability-7"
    assert len(use_case_logs) == 1
    assert use_case_logs[0].request_id == "req-observability-7"
    assert len(seen) == 1
    assert b"req-observability-7" not in seen[0].content


def test_provider_is_counted_once_and_model_is_absent() -> None:
    app, seen = _gemini_app()

    with TestClient(app) as client:
        response = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert response.status_code == 200
    assert len(seen) == 1
    assert _count(app.state.metrics, MetricName.PROVIDER_CALLS_TOTAL, outcome="success") == 1
    assert _count(app.state.metrics, MetricName.PROVIDER_TOKENS_TOTAL, direction="input") == 11
    snapshot = app.state.metrics.snapshot().to_json()
    assert "gemini-3.8-flash-2026-01-01" not in snapshot
    assert "gemini-3.8-flash" not in snapshot


def test_request_id_filter_keeps_explicit_and_neutral_values() -> None:
    def _record() -> logging.LogRecord:
        return logging.LogRecord(
            name="thehouse_genai.providers.gemini",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="provider.call.completed",
            args=(),
            exc_info=None,
        )

    explicit = _record()
    explicit.request_id = "explicit-id"
    assert RequestIdFilter().filter(explicit) is True
    assert explicit.request_id == "explicit-id"

    neutral = _record()
    assert RequestIdFilter().filter(neutral) is True
    assert not hasattr(neutral, "request_id")

    token = request_id_ctx.set("req-from-context")
    try:
        contextual = _record()
        assert RequestIdFilter().filter(contextual) is True
        assert contextual.request_id == "req-from-context"
    finally:
        request_id_ctx.reset(token)
