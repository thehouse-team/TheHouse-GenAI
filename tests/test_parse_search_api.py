"""HTTP integration tests for parse-search.

Every app is built with an offline provider double; no test opens a socket. The endpoint
only delegates to the use case, so these checks cover auth, rate limit, serialization,
safe fallbacks, metrics and headers at the HTTP boundary.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Final

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from thehouse_genai.api.app import create_app
from thehouse_genai.application.budget_port import BudgetSnapshot
from thehouse_genai.application.metrics_port import (
    EndpointPath,
    HttpMethod,
    MetricName,
    StatusClass,
    StatusCode,
)
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.base import (
    GenerativeAiRequest,
    GenerativeAiResponse,
    GenerativeAiUsage,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from thehouse_genai.providers.fake import FakeProvider

URL = "/api/v1/generative/parse-search"
SERVICE_KEY = "test-service-key"
METRICS_KEY = "test-metrics-key"
_REQUEST_ID = "req-parse-search-1"
_UNSET: Final[object] = object()
_FILTER_KEYS = {
    "maxBudget",
    "currency",
    "maxDistanceKm",
    "university",
    "essentialServices",
    "petsAllowed",
}
_SECURITY_HEADERS = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "x-frame-options": "DENY",
}


def _payload(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "query": "Busco algo de máximo 3000 cerca de la UTTT con internet",
        "locale": "es-MX",
    }
    values.update(overrides)
    return values


def _headers() -> dict[str, str]:
    return {"X-Service-Key": SERVICE_KEY}


def _completion(university: str = "UTTT") -> str:
    return json.dumps(
        {
            "filters": {
                "maxBudget": 3000,
                "currency": "MXN",
                "university": university,
                "essentialServices": ["internet"],
                "petsAllowed": None,
                "maxDistanceKm": None,
            }
        },
        ensure_ascii=False,
    )


def _provider(university: str = "UTTT") -> FakeProvider:
    return FakeProvider(text=_completion(university))


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "service_key": SERVICE_KEY,
        "metrics_key": METRICS_KEY,
        "genai_provider": "fake",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _app(provider: object = _UNSET, **overrides: Any) -> FastAPI:
    app = create_app(_settings(**overrides))
    if provider is not _UNSET:
        app.state.provider = provider
    return app


class _ExhaustedBudget:
    """Offline budget double that refuses every call."""

    def reserve_call(self) -> bool:
        return False

    def record_tokens(self, input_tokens: int, output_tokens: int) -> None:
        return None

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            enabled=True,
            exhausted=True,
            day="2026-11-18",
            resets_at="2026-11-19T00:00:00-06:00",
            calls_used=1,
            call_limit=1,
            input_tokens_used=0,
            input_token_limit=None,
            output_tokens_used=0,
            output_token_limit=None,
            estimated_cost="0",
        )


class _ProviderWithModel:
    """Offline provider stub that attaches internal model metadata."""

    async def generate(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        return GenerativeAiResponse(
            text=_completion(),
            usage=GenerativeAiUsage(input_tokens=1, output_tokens=1),
            provider_model="gemini-internal-id",
        )


def _assert_empty_fallback(body: dict[str, Any]) -> None:
    assert set(body) == {"filters", "confidence", "generated", "promptVersion"}
    assert set(body["filters"]) == _FILTER_KEYS
    assert body["filters"] == {
        "maxBudget": None,
        "currency": None,
        "maxDistanceKm": None,
        "university": None,
        "essentialServices": [],
        "petsAllowed": None,
    }
    assert body["confidence"] == "low"
    assert body["generated"] is False
    assert body["promptVersion"] == "parse_search_v1"


def _assert_security_headers(response: Any) -> None:
    for name, expected in _SECURITY_HEADERS.items():
        assert response.headers[name] == expected


class _RecordCollector(logging.Handler):
    """Capture records emitted by one logger, after its filters have run."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _value(app: FastAPI, path: EndpointPath, status: StatusCode) -> int:
    expected = {
        "method": HttpMethod.POST.value,
        "path": path.value,
        "status_code": status.value,
    }
    for counter in app.state.metrics.snapshot().counters:
        if counter.name == MetricName.HTTP_REQUESTS_TOTAL and dict(counter.labels) == expected:
            return counter.value
    return 0


def test_success_has_the_exact_alias_shape() -> None:
    with TestClient(_app(_provider())) as client:
        response = client.post(URL, json=_payload(), headers=_headers())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"filters", "confidence", "generated", "promptVersion"}
    assert set(body["filters"]) == _FILTER_KEYS
    max_budget = body["filters"]["maxBudget"]
    assert isinstance(max_budget, (int, float)) and not isinstance(max_budget, bool)
    assert max_budget == 3000
    assert body["filters"]["currency"] == "MXN"
    assert body["filters"]["university"] == "UTTT"
    assert body["filters"]["essentialServices"] == ["internet"]
    assert body["filters"]["petsAllowed"] is None
    assert body["filters"]["maxDistanceKm"] is None
    assert body["confidence"] == "high"
    assert body["generated"] is True
    assert body["promptVersion"] == "parse_search_v1"


def test_decimal_distance_is_a_json_number() -> None:
    """A value with decimals is a JSON float, never the string of a Decimal."""

    completion = json.dumps(
        {"filters": {"university": "UTTT", "maxDistanceKm": 1.5}}, ensure_ascii=False
    )
    query = "Busco cuarto a menos de 1.5 km de la UTTT"

    with TestClient(_app(FakeProvider(text=completion))) as client:
        response = client.post(URL, json=_payload(query=query), headers=_headers())

    assert response.status_code == 200
    filters = response.json()["filters"]
    distance = filters["maxDistanceKm"]
    assert isinstance(distance, float) and not isinstance(distance, bool)
    assert distance == 1.5
    assert filters["university"] == "UTTT"


def test_null_numeric_filters_stay_null() -> None:
    """Absent numeric filters are emitted as JSON null, not as strings."""

    completion = json.dumps({"filters": {"university": "UTTT"}}, ensure_ascii=False)

    with TestClient(_app(FakeProvider(text=completion))) as client:
        response = client.post(URL, json=_payload(), headers=_headers())

    assert response.status_code == 200
    filters = response.json()["filters"]
    assert filters["maxBudget"] is None
    assert filters["maxDistanceKm"] is None
    assert filters["university"] == "UTTT"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Metrics-Key": METRICS_KEY},
        {"X-Service-Key": "wrong-key"},
    ],
)
def test_unauthorized_uses_the_standard_envelope(headers: dict[str, str]) -> None:
    with TestClient(_app(_provider())) as client:
        response = client.post(URL, json=_payload(), headers=headers)

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "UNAUTHORIZED"
    assert error["message"] == "Authentication required."
    assert error["request_id"]
    _assert_security_headers(response)


def test_rate_limit_returns_retry_after() -> None:
    app = _app(_provider(), rate_limit_requests=1)

    with TestClient(app) as client:
        first = client.post(URL, json=_payload(), headers=_headers())
        response = client.post(URL, json=_payload(), headers=_headers())

    assert first.status_code == 200
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "TOO_MANY_REQUESTS"
    assert int(response.headers["Retry-After"]) >= 1
    _assert_security_headers(response)


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("empty_query", lambda payload: payload.update({"query": ""})),
        ("blank_query", lambda payload: payload.update({"query": "   "})),
        ("oversized_query", lambda payload: payload.update({"query": "A" * 501})),
        ("foreign_locale", lambda payload: payload.update({"locale": "en-US"})),
        ("extra_field", lambda payload: payload.update({"unexpected": 1})),
    ],
)
def test_validation_errors_use_the_standard_envelope(case: str, mutate: Any) -> None:
    payload = _payload()
    mutate(payload)
    provider = _provider()

    with TestClient(_app(provider)) as client:
        response = client.post(URL, json=payload, headers=_headers())

    assert response.status_code == 422, case
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["message"] == "Request validation failed."
    assert provider.calls == []
    _assert_security_headers(response)


def test_auth_is_evaluated_before_body_validation() -> None:
    with TestClient(_app(_provider())) as client:
        response = client.post(URL, json=_payload(query=""), headers={})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize(
    "error",
    [ProviderTimeoutError(), ProviderUnavailableError()],
)
def test_provider_failure_returns_a_safe_fallback(error: Exception) -> None:
    with TestClient(_app(FakeProvider(error=error))) as client:
        response = client.post(URL, json=_payload(), headers=_headers())

    assert response.status_code == 200
    _assert_empty_fallback(response.json())


def test_exhausted_budget_returns_a_safe_fallback() -> None:
    app = _app(_provider())
    app.state.budget = _ExhaustedBudget()

    with TestClient(app) as client:
        response = client.post(URL, json=_payload(), headers=_headers())

    assert response.status_code == 200
    _assert_empty_fallback(response.json())


def test_app_state_moderator_rejects_a_completion_with_pii() -> None:
    """The endpoint uses the shared moderator, not a separate parse-search policy."""

    with TestClient(_app(_provider("UTTT estudiante@ejemplo.mx"))) as client:
        response = client.post(URL, json=_payload(), headers=_headers())

    assert response.status_code == 200
    _assert_empty_fallback(response.json())


def test_provider_model_is_absent_from_the_response() -> None:
    with TestClient(_app(_ProviderWithModel())) as client:
        response = client.post(URL, json=_payload(), headers=_headers())

    assert response.status_code == 200
    assert "provider_model" not in response.json()
    assert "gemini-internal-id" not in response.text


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [(_headers(), 200), ({}, 401)],
)
def test_request_id_is_echoed_on_success_and_errors(
    headers: dict[str, str], expected_status: int
) -> None:
    with TestClient(_app(_provider())) as client:
        response = client.post(
            URL,
            json=_payload(),
            headers={**headers, "X-Request-ID": _REQUEST_ID},
        )

    assert response.status_code == expected_status
    assert response.headers["X-Request-ID"] == _REQUEST_ID
    if expected_status == 401:
        assert response.json()["error"]["request_id"] == _REQUEST_ID
    else:
        assert "error" not in response.json()


def test_parse_search_logs_carry_the_request_id() -> None:
    app = _app(_provider())
    target = logging.getLogger("thehouse_genai.application.parse_search")
    collector = _RecordCollector()
    target.addHandler(collector)
    try:
        with TestClient(app) as client:
            response = client.post(
                URL, json=_payload(), headers={**_headers(), "X-Request-ID": _REQUEST_ID}
            )
    finally:
        target.removeHandler(collector)

    assert response.status_code == 200
    assert collector.records
    assert any(
        getattr(record, "request_id", None) == _REQUEST_ID for record in collector.records
    )


def test_http_metrics_use_the_parse_search_route() -> None:
    app = _app(_provider())

    with TestClient(app) as client:
        response = client.post(URL, json=_payload(), headers=_headers())

    assert response.status_code == 200
    assert _value(app, EndpointPath.PARSE_SEARCH, StatusCode.OK) == 1
    assert _value(app, EndpointPath.OTHER, StatusCode.OK) == 0
    assert _value(app, EndpointPath.EXPLAIN_MATCH, StatusCode.OK) == 0
    expected = {
        "method": HttpMethod.POST.value,
        "path": EndpointPath.PARSE_SEARCH.value,
        "status_class": StatusClass.SUCCESS.value,
    }
    histograms = [
        item
        for item in app.state.metrics.snapshot().histograms
        if item.name == MetricName.HTTP_REQUEST_DURATION_MS and dict(item.labels) == expected
    ]
    assert len(histograms) == 1
    assert histograms[0].count == 1
