"""API error contract and request limit tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import BaseModel

from thehouse_genai.api.app import create_app
from thehouse_genai.infrastructure.config import Settings


def _assert_error_envelope(payload: dict[str, object], code: str) -> None:
    error = payload["error"]
    assert isinstance(error, dict)
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["request_id"], str) and error["request_id"]


def test_not_found_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    _assert_error_envelope(response.json(), "NOT_FOUND")
    assert response.json()["error"]["message"] == "Resource not found."


def test_oversized_request_is_rejected() -> None:
    settings = Settings(app_env="test", max_request_bytes=1_024, _env_file=None)
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/health/live",
            content=b"x" * 2_048,
            headers={"Content-Type": "application/octet-stream"},
        )

    assert response.status_code == 413
    _assert_error_envelope(response.json(), "PAYLOAD_TOO_LARGE")


def test_validation_error_uses_error_envelope() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))

    class Payload(BaseModel):
        name: str

    @app.post("/test/echo")
    async def echo(payload: Payload) -> dict[str, str]:
        return {"name": payload.name}

    with TestClient(app) as client:
        response = client.post("/test/echo", json={})

    assert response.status_code == 422
    _assert_error_envelope(response.json(), "VALIDATION_ERROR")
    assert "name" not in response.text


def test_unhandled_error_hides_internals() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))

    @app.get("/test/boom")
    async def boom() -> None:
        raise RuntimeError("database password leaked here")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test/boom")

    assert response.status_code == 500
    _assert_error_envelope(response.json(), "INTERNAL_ERROR")
    assert "password" not in response.text
    assert "Traceback" not in response.text


def test_cors_is_disabled_by_default(client: TestClient) -> None:
    response = client.get("/health/live", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
