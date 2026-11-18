"""Security response headers and OpenAPI exposure tests."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from thehouse_genai.api.app import create_app
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.fake import FakeProvider

SERVICE_KEY = "test-service-key"
URL = "/api/v1/generative/explain-match"
_EXPECTED_HEADERS = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "x-frame-options": "DENY",
}


def _app(**overrides: Any) -> FastAPI:
    values: dict[str, Any] = {
        "app_env": "test",
        "service_key": SERVICE_KEY,
        "genai_provider": "fake",
    }
    values.update(overrides)
    app = create_app(Settings(_env_file=None, **values))
    app.state.provider = FakeProvider(
        text='{"explanation": "Coincidencia con tus preferencias."}'
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


def _assert_headers(response: Response) -> None:
    for name, expected in _EXPECTED_HEADERS.items():
        assert response.headers[name] == expected


def test_headers_on_success() -> None:
    with TestClient(_app()) as client:
        response = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert response.status_code == 200
    _assert_headers(response)


def test_headers_on_health() -> None:
    with TestClient(_app()) as client:
        for path in ("/health/live", "/health/ready"):
            response = client.get(path)
            assert response.status_code == 200
            _assert_headers(response)


def test_headers_on_401() -> None:
    with TestClient(_app()) as client:
        response = client.post(URL, json=_payload())

    assert response.status_code == 401
    _assert_headers(response)


def test_headers_on_413() -> None:
    with TestClient(_app(max_request_bytes=1_024)) as client:
        response = client.post(
            URL,
            content=b"x" * 2_048,
            headers={"X-Service-Key": SERVICE_KEY, "Content-Type": "application/json"},
        )

    assert response.status_code == 413
    _assert_headers(response)


def test_headers_on_422() -> None:
    payload = _payload()
    del payload["matchScore"]

    with TestClient(_app()) as client:
        response = client.post(URL, json=payload, headers={"X-Service-Key": SERVICE_KEY})

    assert response.status_code == 422
    _assert_headers(response)


def test_headers_on_429() -> None:
    with TestClient(_app(rate_limit_requests=1)) as client:
        first = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        response = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert first.status_code == 200
    assert response.status_code == 429
    _assert_headers(response)


def test_headers_on_500() -> None:
    app = _app()

    @app.get("/test/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test/boom")

    assert response.status_code == 500
    _assert_headers(response)


def test_hsts_and_csp_are_not_set() -> None:
    with TestClient(_app()) as client:
        response = client.get("/health/live")

    assert "strict-transport-security" not in response.headers
    assert "content-security-policy" not in response.headers


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_docs_are_disabled_outside_local_and_test(environment: str) -> None:
    app = _app(app_env=environment)

    assert app.docs_url is None
    assert app.openapi_url is None
    with TestClient(app) as client:
        for path in ("/docs", "/openapi.json"):
            assert client.get(path).status_code == 404


@pytest.mark.parametrize("environment", ["local", "test"])
def test_docs_are_available_in_local_and_test(environment: str) -> None:
    app = _app(app_env=environment)

    assert app.docs_url == "/docs"
    assert app.openapi_url == "/openapi.json"
    with TestClient(app) as client:
        for path in ("/docs", "/openapi.json"):
            assert client.get(path).status_code == 200
