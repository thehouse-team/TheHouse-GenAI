"""Internal diagnostics endpoint tests.

The metrics key is separate from the service key, all rejections use the standard
envelope, and the G01 health probes keep their frozen payload.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from thehouse_genai.api.app import create_app
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.fake import FakeProvider

SERVICE_KEY = "test-service-key"
METRICS_KEY = "test-metrics-key"
URL = "/api/v1/generative/explain-match"
METRICS_URL = "/internal/metrics"
DETAIL_URL = "/internal/health/detail"
_EXPLANATION = "Coincidencia del 87% con tus preferencias."


def _completion() -> str:
    return json.dumps({"explanation": _EXPLANATION}, ensure_ascii=False)


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


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "service_key": SERVICE_KEY,
        "metrics_key": METRICS_KEY,
        "genai_provider": "fake",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _app(**overrides: Any) -> FastAPI:
    app = create_app(_settings(**overrides))
    app.state.provider = FakeProvider(text=_completion())
    return app


def _count(payload: dict[str, Any], name: str, **labels: str) -> int:
    total = 0
    for counter in payload["counters"]:
        if counter["name"] != name:
            continue
        if labels and counter["labels"] != labels:
            continue
        total += int(counter["value"])
    return total


def test_metrics_key_defaults_to_none_and_is_never_in_repr() -> None:
    assert Settings(_env_file=None).metrics_key is None
    assert Settings(_env_file=None, metrics_key="   ").metrics_key is None
    assert METRICS_KEY not in repr(Settings(_env_file=None, metrics_key=METRICS_KEY))


def test_metrics_key_is_read_only_from_its_generated_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GENAI_METRICS_KEY", raising=False)
    monkeypatch.setenv("METRICS_KEY", "generic-must-be-ignored")
    assert Settings(_env_file=None).metrics_key is None

    monkeypatch.setenv("GENAI_METRICS_KEY", METRICS_KEY)
    configured = Settings(_env_file=None).metrics_key
    assert configured is not None
    assert configured.get_secret_value() == METRICS_KEY


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Metrics-Key": "wrong-key"},
        {"X-Service-Key": SERVICE_KEY},
    ],
)
def test_internal_rejections_use_the_standard_envelope(headers: dict[str, str]) -> None:
    with TestClient(_app()) as client:
        response = client.get(METRICS_URL, headers=headers)

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "UNAUTHORIZED"
    assert error["message"] == "Authentication required."
    assert error["request_id"]
    assert response.headers["X-Request-ID"] == error["request_id"]


def test_internal_endpoints_fail_closed_without_a_metrics_key() -> None:
    app = create_app(_settings(metrics_key=None))

    with TestClient(app) as client:
        for path in (METRICS_URL, DETAIL_URL):
            response = client.get(path, headers={"X-Metrics-Key": METRICS_KEY})
            assert response.status_code == 401


def test_metrics_key_opens_internal_endpoints_but_not_explain_match() -> None:
    with TestClient(_app()) as client:
        assert client.get(METRICS_URL, headers={"X-Metrics-Key": METRICS_KEY}).status_code == 200
        assert (
            client.get(DETAIL_URL, headers={"X-Metrics-Key": METRICS_KEY}).status_code == 200
        )
        rejected = client.post(URL, json=_payload(), headers={"X-Metrics-Key": METRICS_KEY})

    assert rejected.status_code == 401


def test_service_key_opens_explain_match_but_not_internal_endpoints() -> None:
    with TestClient(_app()) as client:
        accepted = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        rejected = client.get(METRICS_URL, headers={"X-Service-Key": SERVICE_KEY})

    assert accepted.status_code == 200
    assert rejected.status_code == 401


def test_metrics_snapshot_reflects_real_requests() -> None:
    with TestClient(_app()) as client:
        client.get("/health/live")
        client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        response = client.get(METRICS_URL, headers={"X-Metrics-Key": METRICS_KEY})

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "1"
    names = {counter["name"] for counter in payload["counters"]}
    assert "http_requests_total" in names
    assert "explain_match_outcomes_total" in names
    assert "provider_calls_total" in names
    assert _count(payload, "http_requests_total") >= 2


def test_metrics_key_rejections_have_their_own_counter() -> None:
    with TestClient(_app()) as client:
        client.get(METRICS_URL)
        client.get(METRICS_URL, headers={"X-Metrics-Key": "wrong-key"})
        response = client.get(METRICS_URL, headers={"X-Metrics-Key": METRICS_KEY})

    payload = response.json()
    assert _count(payload, "metrics_auth_rejections_total", reason="missing_key") == 1
    assert _count(payload, "metrics_auth_rejections_total", reason="invalid_key") == 1
    assert _count(payload, "auth_rejections_total") == 0


def test_health_detail_is_ok_with_a_configured_provider() -> None:
    with TestClient(_app()) as client:
        response = client.get(DETAIL_URL, headers={"X-Metrics-Key": METRICS_KEY})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "provider", "moderator", "budget"}
    assert body["status"] == "ok"
    assert body["provider"] == {"configured": True}
    assert body["moderator"] == {"configured": True}
    assert body["budget"]["enabled"] is False
    assert body["budget"]["exhausted"] is False
    assert body["budget"]["resets_at"].endswith("-06:00")


def test_health_detail_is_degraded_without_a_provider() -> None:
    app = create_app(_settings(genai_provider=None))
    assert app.state.provider is None

    with TestClient(app) as client:
        response = client.get(DETAIL_URL, headers={"X-Metrics-Key": METRICS_KEY})

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["provider"] == {"configured": False}


def test_health_detail_is_degraded_when_the_budget_is_exhausted() -> None:
    app = _app(budget_enabled=True, daily_call_limit=1)

    with TestClient(app) as client:
        client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        response = client.get(DETAIL_URL, headers={"X-Metrics-Key": METRICS_KEY})

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["budget"]["exhausted"] is True


def test_health_detail_carries_no_content_or_secret() -> None:
    with TestClient(_app()) as client:
        response = client.get(DETAIL_URL, headers={"X-Metrics-Key": METRICS_KEY})

    lowered = response.text.lower()
    for marker in (SERVICE_KEY, METRICS_KEY, "gemini", "fallback", "exception", "api_key"):
        assert marker not in lowered


def test_g01_health_probes_keep_their_exact_payload() -> None:
    with TestClient(_app()) as client:
        for path in ("/health/live", "/health/ready"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.json() == {
                "status": "ok",
                "service": "thehouse-genai",
                "version": "0.1.0",
            }


def test_cors_allows_the_metrics_key_header() -> None:
    app = _app(cors_origins=["https://app.thehouse.test"])

    with TestClient(app) as client:
        response = client.options(
            METRICS_URL,
            headers={
                "Origin": "https://app.thehouse.test",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-metrics-key",
            },
        )

    assert response.status_code == 200
    assert "x-metrics-key" in response.headers["access-control-allow-headers"].lower()
