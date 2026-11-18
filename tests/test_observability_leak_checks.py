"""No-leak and bounded-cardinality checks for the observability surface.

Markers are injected into every untrusted field and credential, then checked against
the internal endpoints and the captured logs. All traffic stays in-process.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from thehouse_genai.api.app import create_app
from thehouse_genai.application.metrics_port import (
    AuthRejectionReason,
    CallOutcome,
    EndpointPath,
    FallbackReason,
    GeneratedFlag,
    HttpMethod,
    ModerationCategory,
    ModerationDecision,
    ProviderErrorCode,
    StatusClass,
    StatusCode,
    TokenDirection,
)
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.infrastructure.redaction import fingerprint
from thehouse_genai.providers.base import (
    GenerativeAiRequest,
    GenerativeAiResponse,
    GenerativeAiUsage,
    GuardedProvider,
)
from thehouse_genai.providers.gemini import GeminiProvider

SERVICE_KEY = "test-service-key"
METRICS_KEY = "test-metrics-key"
URL = "/api/v1/generative/explain-match"
METRICS_URL = "/internal/metrics"
DETAIL_URL = "/internal/health/detail"

TITLE_MARKER = "title-leak-marker-8f21"
UNIVERSITY_MARKER = "university-leak-marker-a73c"
SERVICE_MARKER = "service-leak-marker-4d90"
PROMPT_MARKER = "prompt-leak-marker-c1e5"
COMPLETION_MARKER = "completion-leak-marker-7b62"
SERVICE_KEY_MARKER = "servicekey-leak-marker-91fa"
METRICS_KEY_MARKER = "metricskey-leak-marker-2e08"
REQUEST_ID_MARKER = "requestid-leak-marker-6c3d"
MODEL_MARKER = "gemini-model-leak-marker-be44"

_ALL_MARKERS = (
    TITLE_MARKER,
    UNIVERSITY_MARKER,
    SERVICE_MARKER,
    PROMPT_MARKER,
    COMPLETION_MARKER,
    SERVICE_KEY_MARKER,
    METRICS_KEY_MARKER,
)

_ALLOWED_LABELS = {
    "method": {item.value for item in HttpMethod},
    "path": {item.value for item in EndpointPath},
    "status_code": {item.value for item in StatusCode},
    "status_class": {item.value for item in StatusClass},
    "outcome": {item.value for item in CallOutcome},
    "code": {item.value for item in ProviderErrorCode},
    "direction": {item.value for item in TokenDirection},
    "generated": {item.value for item in GeneratedFlag},
    "reason": {item.value for item in FallbackReason}
    | {item.value for item in AuthRejectionReason},
    "decision": {item.value for item in ModerationDecision},
    "category": {item.value for item in ModerationCategory},
}


class _MarkingProvider:
    """Offline provider that simulates a prompt and a completion carrying markers."""

    def __init__(self, texts: list[str], prompt_marker: str) -> None:
        self._texts = list(texts)
        self._prompt_marker = prompt_marker
        self.calls: list[GenerativeAiRequest] = []

    async def generate(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        marked = request.model_copy(update={"prompt": f"{request.prompt}\n{self._prompt_marker}"})
        self.calls.append(marked)
        text = self._texts.pop(0) if len(self._texts) > 1 else self._texts[0]
        return GenerativeAiResponse(
            text=text,
            usage=GenerativeAiUsage(input_tokens=11, output_tokens=7),
        )


def _completion(explanation: str) -> str:
    return json.dumps({"explanation": explanation}, ensure_ascii=False)


def _payload() -> dict[str, Any]:
    return {
        "matchScore": 87,
        "university": UNIVERSITY_MARKER,
        "property": {
            "title": TITLE_MARKER,
            "price": 2800,
            "currency": "MXN",
            "distanceKm": 1.2,
            "services": [SERVICE_MARKER],
        },
        "preferences": {
            "budgetMax": 3000,
            "currency": "MXN",
            "maxDistanceKm": 2.0,
            "essentialServices": [SERVICE_MARKER],
        },
    }


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "service_key": SERVICE_KEY,
        "metrics_key": METRICS_KEY,
        "genai_provider": "fake",
        "rate_limit_requests": 2,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _app() -> FastAPI:
    return create_app(_settings())


def _capture(caplog: pytest.LogCaptureFixture) -> None:
    root = logging.getLogger()
    if caplog.handler not in root.handlers:
        root.addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG)


def _logged(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(
        " ".join(str(value) for value in record.__dict__.values()) for record in caplog.records
    )


def _gemini_app() -> FastAPI:
    """Build an app whose adapter reports a marker as the internal model id."""

    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": _completion("Coincidencia del 87% con tus preferencias.")}]
                },
                "finishReason": "STOP",
            }
        ],
        "modelVersion": MODEL_MARKER,
        "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 7},
    }

    def _respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    provider = GuardedProvider(
        GeminiProvider(
            api_key=SecretStr("test-key-not-a-real-credential"),
            model="gemini-3.8-flash",
            timeout_seconds=1.0,
            client=httpx.AsyncClient(transport=httpx.MockTransport(_respond)),
        ),
        timeout_seconds=1.0,
        max_input_chars=4_000,
    )
    app = create_app(_settings())
    app.state.provider = provider
    return app


def _items(snapshot: dict[str, Any], family: str) -> Iterator[dict[str, Any]]:
    yield from snapshot[family]


def test_markers_never_reach_metrics_logs_or_detail(caplog: pytest.LogCaptureFixture) -> None:
    app = _app()
    provider = _MarkingProvider(
        [
            _completion("Coincidencia del 87% con tus preferencias."),
            _completion(f"Coincidencia del 87% con tus preferencias. 9999 {COMPLETION_MARKER}"),
        ],
        PROMPT_MARKER,
    )
    app.state.provider = provider
    _capture(caplog)

    with TestClient(app) as client:
        payload = _payload()
        success = client.post(
            URL,
            json=payload,
            headers={"X-Service-Key": SERVICE_KEY, "X-Request-ID": REQUEST_ID_MARKER},
        )
        fallback = client.post(URL, json=payload, headers={"X-Service-Key": SERVICE_KEY})
        bad_service_key = client.post(
            URL, json=payload, headers={"X-Service-Key": SERVICE_KEY_MARKER}
        )
        bad_metrics_key = client.get(
            METRICS_URL, headers={"X-Metrics-Key": METRICS_KEY_MARKER}
        )
        limited = client.post(URL, json=payload, headers={"X-Service-Key": SERVICE_KEY})
        metrics = client.get(METRICS_URL, headers={"X-Metrics-Key": METRICS_KEY})
        detail = client.get(DETAIL_URL, headers={"X-Metrics-Key": METRICS_KEY})

    assert success.status_code == 200 and success.json()["generated"] is True
    assert fallback.status_code == 200 and fallback.json()["generated"] is False
    assert bad_service_key.status_code == 401
    assert bad_metrics_key.status_code == 401
    assert limited.status_code == 429
    assert metrics.status_code == 200 and detail.status_code == 200
    assert any(PROMPT_MARKER in call.prompt for call in provider.calls)

    for marker in _ALL_MARKERS:
        assert marker not in metrics.text
        assert marker not in detail.text
        assert marker not in _logged(caplog)

    assert REQUEST_ID_MARKER not in metrics.text
    assert REQUEST_ID_MARKER not in detail.text
    for value in (SERVICE_KEY, SERVICE_KEY_MARKER, METRICS_KEY, METRICS_KEY_MARKER):
        assert fingerprint(value) not in metrics.text


def test_every_snapshot_label_belongs_to_a_closed_enum() -> None:
    app = _app()

    with TestClient(app) as client:
        client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        client.post(URL, json=_payload())
        snapshot = client.get(METRICS_URL, headers={"X-Metrics-Key": METRICS_KEY}).json()

    for family in ("counters", "histograms", "gauges"):
        for item in _items(snapshot, family):
            for key, value in item["labels"].items():
                assert key in _ALLOWED_LABELS, (family, key)
                assert value in _ALLOWED_LABELS[key], (family, key, value)

    assert snapshot["counters"]


def test_unknown_and_id_paths_are_grouped_as_other() -> None:
    app = _app()

    with TestClient(app) as client:
        for index in range(200):
            assert client.get(f"/unknown/path-{index}").status_code == 404
        assert client.get(f"{URL}/deadbeef0123456789").status_code == 404
        snapshot = client.get(METRICS_URL, headers={"X-Metrics-Key": METRICS_KEY}).json()

    counters = [
        item for item in snapshot["counters"] if item["name"] == "http_requests_total"
    ]
    paths = {item["labels"]["path"] for item in counters}
    assert paths == {"other"}
    assert sum(item["value"] for item in counters) == 201
    histograms = [
        item for item in snapshot["histograms"] if item["name"] == "http_request_duration_ms"
    ]
    assert {item["labels"]["path"] for item in histograms} == {"other"}
    assert {item["labels"]["status_class"] for item in histograms} == {"4xx"}
    assert len(histograms) == 1


def test_provider_model_never_appears_in_metrics() -> None:
    app = _gemini_app()

    with TestClient(app) as client:
        client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        metrics = client.get(METRICS_URL, headers={"X-Metrics-Key": METRICS_KEY})

    assert MODEL_MARKER not in metrics.text
    assert "provider_model" not in metrics.json()
