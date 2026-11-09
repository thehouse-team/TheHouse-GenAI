"""Foundation health probe tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_live_returns_200(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "thehouse-genai",
        "version": "0.1.0",
    }


def test_ready_returns_200(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "thehouse-genai"


def test_health_response_has_request_id(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "req-test-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-123"


def test_unsafe_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "bad id\nwith newline"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "bad id\nwith newline"
    assert response.headers["X-Request-ID"].isalnum()
