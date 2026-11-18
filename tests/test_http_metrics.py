"""HTTP metrics integration tests.

Every request goes through an in-process TestClient with a FakeProvider: no socket, no
credential, and no raw URL or query string in the metric vocabulary.
"""

from __future__ import annotations

import json
from typing import Any, Final

from fastapi import FastAPI
from fastapi.testclient import TestClient

from thehouse_genai.api.app import create_app
from thehouse_genai.application.metrics_port import (
    EndpointPath,
    HttpMethod,
    MetricName,
    MetricsRecorder,
    StatusCode,
)
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.fake import FakeProvider

URL = "/api/v1/generative/explain-match"
SERVICE_KEY = "test-service-key"
_MARKER: Final[str] = "marker-that-must-not-leak-xyz"


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "service_key": SERVICE_KEY,
        "genai_provider": "fake",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _app(**overrides: Any) -> FastAPI:
    app = create_app(_settings(**overrides))
    app.state.provider = FakeProvider(
        text=json.dumps({"explanation": "Coincidencia del 87% con tus preferencias."})
    )
    return app


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


def _value(
    app: FastAPI,
    method: HttpMethod,
    path: EndpointPath,
    status: StatusCode,
) -> int:
    expected = {"method": method.value, "path": path.value, "status_code": status.value}
    for counter in app.state.metrics.snapshot().counters:
        if counter.name == MetricName.HTTP_REQUESTS_TOTAL and dict(counter.labels) == expected:
            return counter.value
    return 0


def _histogram(
    app: FastAPI,
    method: HttpMethod,
    path: EndpointPath,
) -> Any:
    expected = {"method": method.value, "path": path.value}
    for histogram in app.state.metrics.snapshot().histograms:
        if (
            histogram.name == MetricName.HTTP_REQUEST_DURATION_MS
            and dict(histogram.labels) == expected
        ):
            return histogram
    return None


def test_metrics_registry_lives_in_app_state() -> None:
    app = create_app(_settings())

    assert isinstance(app.state.metrics, MetricsRecorder)


def test_health_routes_are_counted() -> None:
    app = _app()

    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200

    assert _value(app, HttpMethod.GET, EndpointPath.LIVE, StatusCode.OK) == 1
    assert _value(app, HttpMethod.GET, EndpointPath.READY, StatusCode.OK) == 1


def test_success_is_counted_with_a_latency_histogram() -> None:
    app = _app()

    with TestClient(app) as client:
        response = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert response.status_code == 200
    assert _value(app, HttpMethod.POST, EndpointPath.EXPLAIN_MATCH, StatusCode.OK) == 1
    histogram = _histogram(app, HttpMethod.POST, EndpointPath.EXPLAIN_MATCH)
    assert histogram is not None
    assert histogram.count == 1
    assert histogram.total_ms >= 0
    assert histogram.p95_ms_approx >= 0


def test_401_is_counted() -> None:
    app = _app()

    with TestClient(app) as client:
        response = client.post(URL, json=_payload())

    assert response.status_code == 401
    assert _value(app, HttpMethod.POST, EndpointPath.EXPLAIN_MATCH, StatusCode.UNAUTHORIZED) == 1


def test_413_is_counted() -> None:
    app = _app(max_request_bytes=1_024)

    with TestClient(app) as client:
        response = client.post(
            URL,
            content=b"x" * 2_048,
            headers={"X-Service-Key": SERVICE_KEY, "Content-Type": "application/json"},
        )

    assert response.status_code == 413
    expected = StatusCode.PAYLOAD_TOO_LARGE
    assert _value(app, HttpMethod.POST, EndpointPath.EXPLAIN_MATCH, expected) == 1


def test_422_is_counted() -> None:
    app = _app()
    payload = _payload()
    del payload["matchScore"]

    with TestClient(app) as client:
        response = client.post(URL, json=payload, headers={"X-Service-Key": SERVICE_KEY})

    assert response.status_code == 422
    expected = StatusCode.VALIDATION_ERROR
    assert _value(app, HttpMethod.POST, EndpointPath.EXPLAIN_MATCH, expected) == 1


def test_429_is_counted() -> None:
    app = _app(rate_limit_requests=1)

    with TestClient(app) as client:
        first = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        response = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert first.status_code == 200

    assert response.status_code == 429
    expected = StatusCode.TOO_MANY_REQUESTS
    assert _value(app, HttpMethod.POST, EndpointPath.EXPLAIN_MATCH, expected) == 1


def test_500_is_counted() -> None:
    app = _app()

    @app.get("/test/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test/boom")

    assert response.status_code == 500
    assert _value(app, HttpMethod.GET, EndpointPath.OTHER, StatusCode.INTERNAL_ERROR) == 1


def test_unknown_route_is_counted_as_other() -> None:
    app = _app()

    with TestClient(app) as client:
        response = client.get("/not-a-known-route")

    assert response.status_code == 404
    assert _value(app, HttpMethod.GET, EndpointPath.OTHER, StatusCode.NOT_FOUND) == 1


def test_id_like_path_is_counted_as_other() -> None:
    app = _app()

    with TestClient(app) as client:
        response = client.get(f"{URL}/abcd1234ef567890")

    assert response.status_code == 404
    assert _value(app, HttpMethod.GET, EndpointPath.OTHER, StatusCode.NOT_FOUND) == 1


def test_query_string_never_reaches_the_labels() -> None:
    app = _app()

    with TestClient(app) as client:
        response = client.get(f"/health/live?marker={_MARKER}")

    assert response.status_code == 200
    snapshot = app.state.metrics.snapshot().to_json()
    assert _MARKER not in snapshot
    assert _value(app, HttpMethod.GET, EndpointPath.LIVE, StatusCode.OK) == 1


def test_explain_match_contract_is_unchanged() -> None:
    app = _app()

    with TestClient(app) as client:
        response = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert response.status_code == 200
    assert set(response.json()) == {"explanation", "generated", "promptVersion"}
