"""Service key rotation tests.

During rotation both the current and the previous `X-Service-Key` are accepted. A
previous key alone never authenticates, and every rejection still uses the same safe
401 envelope from spec 003.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from httpx import Response

from thehouse_genai.api import auth as auth_module
from thehouse_genai.api.app import create_app
from thehouse_genai.api.auth import require_service_key
from thehouse_genai.infrastructure.config import Settings

CURRENT_KEY = "current-service-key"
PREVIOUS_KEY = "previous-service-key"
PROTECTED_PATH = "/test/protected"


def _settings(**overrides: Any) -> Settings:
    """Build deterministic settings with both rotation keys configured."""

    values: dict[str, Any] = {
        "app_env": "test",
        "service_key": CURRENT_KEY,
        "service_key_previous": PREVIOUS_KEY,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _client(settings: Settings) -> TestClient:
    """Create an app with a test-only route guarded by the dependency."""

    app = create_app(settings)

    @app.get(PROTECTED_PATH, dependencies=[Depends(require_service_key)])
    async def protected() -> dict[str, str]:
        return {"status": "ok"}

    return TestClient(app)


def _rejection_body(response: Response) -> dict[str, str]:
    """Return the comparable fields of a 401 response body."""

    error = response.json()["error"]
    return {"code": error["code"], "message": error["message"]}


def test_current_key_is_accepted_during_rotation() -> None:
    with _client(_settings()) as client:
        response = client.get(PROTECTED_PATH, headers={"X-Service-Key": CURRENT_KEY})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_previous_key_is_accepted_during_rotation() -> None:
    with _client(_settings()) as client:
        response = client.get(PROTECTED_PATH, headers={"X-Service-Key": PREVIOUS_KEY})

    assert response.status_code == 200


def test_unknown_key_is_rejected_during_rotation() -> None:
    with _client(_settings()) as client:
        response = client.get(PROTECTED_PATH, headers={"X-Service-Key": "unknown-key"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_missing_key_is_rejected_during_rotation() -> None:
    with _client(_settings()) as client:
        response = client.get(PROTECTED_PATH)

    assert response.status_code == 401


def test_only_previous_key_fails_closed() -> None:
    with _client(_settings(service_key=None)) as client:
        response = client.get(PROTECTED_PATH, headers={"X-Service-Key": PREVIOUS_KEY})

    assert response.status_code == 401


def test_every_rejection_has_the_same_body() -> None:
    configured = _client(_settings())
    unconfigured = _client(_settings(service_key=None))
    with configured, unconfigured:
        missing = configured.get(PROTECTED_PATH)
        wrong = configured.get(PROTECTED_PATH, headers={"X-Service-Key": "unknown-key"})
        only_previous = unconfigured.get(
            PROTECTED_PATH, headers={"X-Service-Key": PREVIOUS_KEY}
        )

    assert [response.status_code for response in (missing, wrong, only_previous)] == [
        401,
        401,
        401,
    ]
    assert _rejection_body(missing) == _rejection_body(wrong) == _rejection_body(only_previous)


def test_every_configured_key_is_compared_even_when_the_current_one_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compared: list[str] = []
    original = auth_module.compare_digest

    def _recording(presented: bytes, expected: bytes) -> bool:
        compared.append(expected.decode("utf-8"))
        return original(presented, expected)

    monkeypatch.setattr(auth_module, "compare_digest", _recording)

    with _client(_settings()) as client:
        response = client.get(PROTECTED_PATH, headers={"X-Service-Key": CURRENT_KEY})

    assert response.status_code == 200
    assert compared == [CURRENT_KEY, PREVIOUS_KEY]


def test_previous_key_never_appears_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)

    with _client(_settings()) as client:
        client.get(PROTECTED_PATH, headers={"X-Service-Key": PREVIOUS_KEY})
        client.get(PROTECTED_PATH, headers={"X-Service-Key": "unknown-key"})

    logged = "\n".join(
        " ".join(str(value) for value in record.__dict__.values()) for record in caplog.records
    )
    assert PREVIOUS_KEY not in logged
    assert CURRENT_KEY not in logged
    assert "unknown-key" not in logged
