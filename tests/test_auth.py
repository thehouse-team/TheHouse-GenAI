"""Service key authentication tests.

The protected route exists only in this test module: the real application does not
expose it until the explain-match endpoint is wired in a later block.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from httpx import Response

from thehouse_genai.api.app import create_app
from thehouse_genai.api.auth import require_service_key
from thehouse_genai.infrastructure.config import Settings

VALID_KEY = "test-service-key"
PROTECTED_PATH = "/test/protected"


def _settings(**overrides: Any) -> Settings:
    """Build deterministic settings with a configured service key."""

    values: dict[str, Any] = {"app_env": "test", "service_key": VALID_KEY}
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _client(settings: Settings) -> TestClient:
    """Create an app with a test-only route guarded by the dependency."""

    app = create_app(settings)

    @app.get(PROTECTED_PATH, dependencies=[Depends(require_service_key)])
    async def protected() -> dict[str, str]:
        return {"status": "ok"}

    return TestClient(app)


def _assert_envelope(payload: dict[str, Any]) -> None:
    """Check the standard error envelope of a rejected request."""

    error = payload["error"]
    assert error["code"] == "UNAUTHORIZED"
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["request_id"], str) and error["request_id"]


def _rejection_body(response: Response) -> dict[str, Any]:
    """Return the comparable fields of a 401 response body."""

    error = response.json()["error"]
    return {"code": error["code"], "message": error["message"]}


def test_protected_route_is_not_in_the_real_app(client: TestClient) -> None:
    assert client.get(PROTECTED_PATH).status_code == 404


def test_missing_header_returns_401() -> None:
    with _client(_settings()) as client:
        response = client.get(PROTECTED_PATH)

    assert response.status_code == 401
    _assert_envelope(response.json())


def test_wrong_key_returns_401() -> None:
    with _client(_settings()) as client:
        response = client.get(PROTECTED_PATH, headers={"X-Service-Key": "wrong-key"})

    assert response.status_code == 401
    _assert_envelope(response.json())


def test_unconfigured_credential_returns_401() -> None:
    with _client(_settings(service_key=None)) as client:
        response = client.get(PROTECTED_PATH, headers={"X-Service-Key": VALID_KEY})

    assert response.status_code == 401
    _assert_envelope(response.json())


def test_every_rejection_has_the_same_body() -> None:
    with _client(_settings()) as configured, _client(_settings(service_key=None)) as unconfigured:
        missing = configured.get(PROTECTED_PATH)
        wrong = configured.get(PROTECTED_PATH, headers={"X-Service-Key": "wrong-key"})
        unset = unconfigured.get(PROTECTED_PATH, headers={"X-Service-Key": VALID_KEY})

    assert [response.status_code for response in (missing, wrong, unset)] == [401, 401, 401]
    assert _rejection_body(missing) == _rejection_body(wrong) == _rejection_body(unset)


def test_envelope_carries_the_request_id() -> None:
    with _client(_settings()) as client:
        response = client.get(PROTECTED_PATH, headers={"X-Request-ID": "req-auth-1"})

    assert response.status_code == 401
    assert response.json()["error"]["request_id"] == "req-auth-1"
    assert response.headers["X-Request-ID"] == "req-auth-1"


def test_correct_key_is_accepted() -> None:
    with _client(_settings()) as client:
        response = client.get(PROTECTED_PATH, headers={"X-Service-Key": VALID_KEY})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_lowercase_header_is_accepted() -> None:
    with _client(_settings()) as client:
        response = client.get(PROTECTED_PATH, headers={"x-service-key": VALID_KEY})

    assert response.status_code == 200


def test_key_never_appears_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with _client(_settings()) as client:
        client.get(PROTECTED_PATH, headers={"X-Service-Key": VALID_KEY})
        client.get(PROTECTED_PATH, headers={"X-Service-Key": "wrong-key"})

    logged = "\n".join(
        " ".join(str(value) for value in record.__dict__.values()) for record in caplog.records
    )

    assert VALID_KEY not in logged
    assert "wrong-key" not in logged


def test_auth_module_does_not_use_the_cached_settings() -> None:
    auth_source = Path(__file__).resolve().parents[1] / "src" / "thehouse_genai" / "api" / "auth.py"
    source = auth_source.read_text(encoding="utf-8")

    assert "get_settings" not in source
    assert "request.app.state.settings" in source
