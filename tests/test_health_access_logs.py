"""Successful health probes must not flood the INFO access log (spec 009, B6).

Metrics still count every probe and failed health requests stay at INFO.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from thehouse_genai.api.app import create_app
from thehouse_genai.api.middleware import RequestContextMiddleware
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.infrastructure.metrics import MetricsRegistry

ACCESS_EVENT = "http.request.completed"


def _capture(caplog: pytest.LogCaptureFixture) -> None:
    """Re-attach caplog's handler after `create_app` clears the root handlers."""

    root = logging.getLogger()
    if caplog.handler not in root.handlers:
        root.addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG)


def _access_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.getMessage() == ACCESS_EVENT]


def _app() -> FastAPI:
    return create_app(Settings(_env_file=None, app_env="test", genai_provider="fake"))


@pytest.mark.parametrize("path", ["/health/live", "/health/ready"])
def test_successful_health_probe_is_logged_at_debug(
    path: str, caplog: pytest.LogCaptureFixture
) -> None:
    app = _app()
    _capture(caplog)

    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 200
    records = _access_records(caplog)
    assert len(records) == 1
    assert records[0].levelno == logging.DEBUG
    assert records[0].path == path
    assert records[0].status_code == 200


def test_non_health_request_stays_at_info(caplog: pytest.LogCaptureFixture) -> None:
    app = _app()
    _capture(caplog)

    with TestClient(app) as client:
        response = client.get("/does-not-exist")

    assert response.status_code == 404
    records = _access_records(caplog)
    assert len(records) == 1
    assert records[0].levelno == logging.INFO
    assert records[0].status_code == 404


def _status_app(status: int) -> ASGIApp:
    """Minimal ASGI app with a fixed status, used to force a failing health probe."""

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
            return
        if scope["type"] != "http":
            return
        start: Message = {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-length", b"0")],
        }
        await send(start)
        await send({"type": "http.response.body", "body": b""})

    return app


def test_failing_health_probe_is_still_logged_at_info(
    caplog: pytest.LogCaptureFixture,
) -> None:
    wrapped: Any = RequestContextMiddleware(
        _status_app(500), metrics=MetricsRegistry()
    )
    root = logging.getLogger()
    if caplog.handler not in root.handlers:
        root.addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG)

    with TestClient(wrapped) as client:
        response = client.get("/health/live")

    assert response.status_code == 500
    records = _access_records(caplog)
    assert len(records) == 1
    assert records[0].levelno == logging.INFO
    assert records[0].status_code == 500


def test_health_probes_are_still_counted_in_metrics() -> None:
    app = _app()

    with TestClient(app) as client:
        client.get("/health/live")
        client.get("/health/ready")

    counted: dict[str, int] = {}
    for counter in app.state.metrics.snapshot().counters:
        labels = dict(counter.labels)
        if counter.name == "http_requests_total" and labels["method"] == "GET":
            counted[labels["path"]] = counter.value
    assert counted["/health/live"] == 1
    assert counted["/health/ready"] == 1
