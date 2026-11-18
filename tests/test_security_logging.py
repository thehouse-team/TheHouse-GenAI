"""Security event logging tests.

Every rejection logs only a bounded reason and a request ID. Credentials, request
bodies and fields outside the formatter allowlist never reach a log line.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from thehouse_genai.api.app import create_app
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.infrastructure.logging import JsonFormatter
from thehouse_genai.infrastructure.redaction import fingerprint
from thehouse_genai.providers.fake import FakeProvider

SERVICE_KEY = "configured-secret-value-xyz"
PRESENTED_KEY = "presented-secret-value-xyz"
URL = "/api/v1/generative/explain-match"
TITLE_MARKER = "CuerpoSecretoUnico987"


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
            "title": TITLE_MARKER,
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


def _capture(caplog: pytest.LogCaptureFixture) -> None:
    """Re-attach caplog's handler after `create_app` clears the root handlers."""

    root = logging.getLogger()
    if caplog.handler not in root.handlers:
        root.addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG)


def _records(caplog: pytest.LogCaptureFixture, message: str) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.getMessage() == message]


def _logged_text(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(
        " ".join(str(value) for value in record.__dict__.values()) for record in caplog.records
    )


@pytest.mark.parametrize(
    ("overrides", "headers", "expected"),
    [
        ({}, {}, "missing_key"),
        ({}, {"X-Service-Key": PRESENTED_KEY}, "invalid_key"),
        ({"service_key": None}, {"X-Service-Key": PRESENTED_KEY}, "not_configured"),
    ],
)
def test_each_401_reason_is_logged(
    overrides: dict[str, Any],
    headers: dict[str, str],
    expected: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = _app(**overrides)
    _capture(caplog)

    with TestClient(app) as client:
        response = client.post(URL, json=_payload(), headers=headers)

    assert response.status_code == 401
    records = _records(caplog, "auth.rejected")
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert records[0].reason == expected
    assert records[0].request_id == response.json()["error"]["request_id"]


def test_all_401_bodies_are_identical(caplog: pytest.LogCaptureFixture) -> None:
    configured = _app()
    unconfigured = _app(service_key=None)
    _capture(caplog)

    with (
        TestClient(configured) as configured_client,
        TestClient(unconfigured) as unconfigured_client,
    ):
        missing = configured_client.post(URL, json=_payload())
        invalid = configured_client.post(
            URL, json=_payload(), headers={"X-Service-Key": PRESENTED_KEY}
        )
        unset = unconfigured_client.post(
            URL, json=_payload(), headers={"X-Service-Key": PRESENTED_KEY}
        )

    def _body(response: Any) -> dict[str, str]:
        error = response.json()["error"]
        return {"code": error["code"], "message": error["message"]}

    assert [response.status_code for response in (missing, invalid, unset)] == [401, 401, 401]
    assert _body(missing) == _body(invalid) == _body(unset)


def test_429_logs_request_id_reason_client_and_retry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = _app(rate_limit_requests=1)
    _capture(caplog)

    with TestClient(app) as client:
        first = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        response = client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert first.status_code == 200

    assert response.status_code == 429
    records = _records(caplog, "rate_limit.rejected")
    assert len(records) == 1
    record = records[0]
    assert record.levelno == logging.WARNING
    assert record.reason == "limit_exceeded"
    assert record.request_id == response.json()["error"]["request_id"]
    assert record.client_id == fingerprint(SERVICE_KEY)
    assert record.retry_after_seconds == 60


def test_credentials_and_body_never_appear_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    app = _app(rate_limit_requests=1)
    _capture(caplog)

    with TestClient(app) as client:
        client.post(URL, json=_payload(), headers={"X-Service-Key": PRESENTED_KEY})
        client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})
        client.post(URL, json=_payload(), headers={"X-Service-Key": SERVICE_KEY})

    assert _records(caplog, "auth.rejected")
    assert _records(caplog, "rate_limit.rejected")
    logged = _logged_text(caplog)
    for secret in (SERVICE_KEY, PRESENTED_KEY, TITLE_MARKER):
        assert secret not in logged


def test_json_formatter_emits_only_allowlisted_extra_fields() -> None:
    record = logging.LogRecord(
        name="thehouse_genai.api.auth",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="auth.rejected",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-1"
    record.reason = "missing_key"
    record.client_id = "0123456789abcdef"
    record.retry_after_seconds = 60
    record.unlisted_field = "value-that-must-not-leak-xyz"
    record.body = TITLE_MARKER

    payload = json.loads(JsonFormatter().format(record))

    assert payload["reason"] == "missing_key"
    assert payload["client_id"] == "0123456789abcdef"
    assert payload["retry_after_seconds"] == 60
    assert "value-that-must-not-leak-xyz" not in payload
    assert TITLE_MARKER not in payload
    assert "unlisted_field" not in payload
    assert "body" not in payload
