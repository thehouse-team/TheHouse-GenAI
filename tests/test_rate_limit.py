"""In-process rate limiting tests.

The fake clock makes the fixed window deterministic. No test opens a socket and no
credential is written to the limiter state or to logs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from thehouse_genai.api.app import create_app
from thehouse_genai.api.rate_limit import InMemoryRateLimiter
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.infrastructure.redaction import fingerprint
from thehouse_genai.providers.fake import FakeProvider

SERVICE_KEY = "current-service-key"
PREVIOUS_KEY = "previous-service-key"
URL = "/api/v1/generative/explain-match"


@pytest.fixture()
def now(monkeypatch: pytest.MonkeyPatch) -> dict[str, float]:
    """Install a deterministic monotonic clock and return its mutable value."""

    clock = {"value": 1_000.0}
    monkeypatch.setattr("thehouse_genai.api.rate_limit.monotonic", lambda: clock["value"])
    return clock


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


def _app(**overrides: Any) -> FastAPI:
    values: dict[str, Any] = {
        "app_env": "test",
        "service_key": SERVICE_KEY,
        "service_key_previous": PREVIOUS_KEY,
        "genai_provider": "fake",
        "rate_limit_requests": 2,
        "rate_limit_window_seconds": 60,
        "rate_limit_max_clients": 10,
    }
    values.update(overrides)
    settings = Settings(_env_file=None, **values)
    app = create_app(settings)
    app.state.provider = FakeProvider(
        text=json.dumps({"explanation": "Coincidencia con tus preferencias."})
    )
    return app


def _post(client: TestClient, key: str | None = SERVICE_KEY) -> Any:
    headers = {} if key is None else {"X-Service-Key": key}
    return client.post(URL, json=_payload(), headers=headers)


def test_fingerprint_is_a_short_stable_hex_digest() -> None:
    value = "a-service-key"

    result = fingerprint(value)

    assert result == fingerprint(value)
    assert len(result) == 16
    assert value not in result
    assert all(char in "0123456789abcdef" for char in result)


def test_requests_within_the_limit_succeed(now: dict[str, float]) -> None:
    with TestClient(_app()) as client:
        assert _post(client).status_code == 200
        assert _post(client).status_code == 200


def test_exceeding_the_limit_returns_429_with_retry_after(now: dict[str, float]) -> None:
    with TestClient(_app()) as client:
        assert _post(client).status_code == 200
        assert _post(client).status_code == 200
        response = _post(client)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "TOO_MANY_REQUESTS"
    assert response.json()["error"]["message"] == "Too many requests."
    assert response.headers["Retry-After"] == "60"


def test_window_resets_with_the_fake_clock(now: dict[str, float]) -> None:
    with TestClient(_app()) as client:
        assert _post(client).status_code == 200
        assert _post(client).status_code == 200
        assert _post(client).status_code == 429
        now["value"] += 61
        assert _post(client).status_code == 200


def test_current_and_previous_keys_have_separate_budgets(now: dict[str, float]) -> None:
    with TestClient(_app(rate_limit_requests=1)) as client:
        assert _post(client, SERVICE_KEY).status_code == 200
        assert _post(client, PREVIOUS_KEY).status_code == 200
        assert _post(client, SERVICE_KEY).status_code == 429


def test_unauthenticated_requests_do_not_consume_a_budget(
    now: dict[str, float], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    with TestClient(_app(rate_limit_requests=1)) as client:
        assert _post(client, None).status_code == 401
        assert _post(client).status_code == 200

    assert "rate_limit.rejected" not in [record.getMessage() for record in caplog.records]


def test_health_is_never_limited(now: dict[str, float]) -> None:
    with TestClient(_app(rate_limit_requests=1)) as client:
        statuses = [client.get("/health/live").status_code for _ in range(3)]
        statuses += [client.get("/health/ready").status_code for _ in range(3)]

    assert statuses == [200] * 6


def test_limiter_prunes_expired_and_oldest_clients(now: dict[str, float]) -> None:
    limiter = InMemoryRateLimiter(
        requests=1,
        window_seconds=10,
        max_clients=2,
        clock=lambda: now["value"],
    )

    assert limiter.check("a")[0] is True
    assert limiter.check("b")[0] is True
    assert limiter.check("c")[0] is True
    assert len(limiter.tracked_clients) == 2
    assert "a" not in limiter.tracked_clients

    now["value"] += 11
    limiter.check("d")
    assert "b" not in limiter.tracked_clients
    assert "c" not in limiter.tracked_clients


def test_disabled_rate_limit_does_not_limit(now: dict[str, float]) -> None:
    with TestClient(_app(rate_limit_enabled=False, rate_limit_requests=1)) as client:
        statuses = [_post(client).status_code for _ in range(4)]

    assert statuses == [200] * 4


def test_key_never_appears_in_state_or_logs(
    now: dict[str, float], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    app = _app(rate_limit_requests=1)
    limiter: InMemoryRateLimiter = app.state.rate_limiter

    with TestClient(app) as client:
        assert _post(client).status_code == 200
        assert _post(client).status_code == 429

    tracked = limiter.tracked_clients
    assert tracked
    assert all(len(item) == 16 for item in tracked)
    assert all(SERVICE_KEY not in item and PREVIOUS_KEY not in item for item in tracked)
    logged = "\n".join(
        " ".join(str(value) for value in record.__dict__.values()) for record in caplog.records
    )
    assert SERVICE_KEY not in logged
    assert PREVIOUS_KEY not in logged


def test_arbitrary_exception_headers_are_not_forwarded(now: dict[str, float]) -> None:
    app = _app()

    @app.get("/test/leaky")
    async def leaky() -> None:
        raise HTTPException(
            status_code=400,
            headers={"X-Secret": "leak-me", "X-Request-ID": "spoofed"},
        )

    with TestClient(app) as client:
        response = client.get("/test/leaky")

    assert response.status_code == 400
    assert "x-secret" not in response.headers
    assert response.headers["X-Request-ID"] != "spoofed"
