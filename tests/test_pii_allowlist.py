"""PII minimization tests for the explain-match prompt.

The allowlist is the source of truth for the fields that may reach the LLM. A test fails
if the request schema or the context serialization drifts away from it, or if a new
field carries a sensitive name.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from thehouse_genai.api.app import create_app
from thehouse_genai.domain.match_explanation import (
    PROMPT_FIELD_ALLOWLIST,
    ExplainMatchRequest,
)
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.fake import FakeProvider

SERVICE_KEY = "test-service-key"
URL = "/api/v1/generative/explain-match"
_SENSITIVE_FIELDS = frozenset(
    {"ownerName", "address", "accessToken", "refreshToken", "password", "authorization"}
)


def _payload() -> dict[str, Any]:
    """Build a valid canonical request with the Backend aliases."""

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


def _collect_aliases(model: type[BaseModel], prefix: str = "") -> frozenset[str]:
    """Collect every field alias of a model and its nested models recursively."""

    aliases: set[str] = set()
    for name, field in model.model_fields.items():
        alias = field.alias or name
        path = f"{prefix}.{alias}" if prefix else alias
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            aliases.update(_collect_aliases(annotation, path))
        else:
            aliases.add(path)
    return frozenset(aliases)


def test_allowlist_has_exactly_twelve_fields() -> None:
    assert len(PROMPT_FIELD_ALLOWLIST) == 12


def test_prompt_field_allowlist_matches_the_request_schema() -> None:
    assert _collect_aliases(ExplainMatchRequest) == PROMPT_FIELD_ALLOWLIST


def test_to_context_emits_only_allowlisted_keys() -> None:
    context = ExplainMatchRequest.model_validate(_payload()).to_context()

    keys = {line.split(": ", 1)[0] for line in context.splitlines()}
    assert keys == PROMPT_FIELD_ALLOWLIST


def test_allowlist_excludes_sensitive_fields() -> None:
    assert not (PROMPT_FIELD_ALLOWLIST & _SENSITIVE_FIELDS)
    assert not (_collect_aliases(ExplainMatchRequest) & _SENSITIVE_FIELDS)


def test_access_token_payload_is_rejected_without_reaching_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    injected_value = "value-that-must-not-leak-123"
    payload = _payload()
    payload["accessToken"] = injected_value

    settings = Settings(
        app_env="test",
        service_key=SERVICE_KEY,
        genai_provider="fake",
        _env_file=None,
    )
    app = create_app(settings)
    provider = FakeProvider(text=json.dumps({"explanation": "Coincidencia."}))
    app.state.provider = provider

    with TestClient(app) as client:
        response = client.post(URL, json=payload, headers={"X-Service-Key": SERVICE_KEY})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert provider.calls == []
    logged = "\n".join(
        " ".join(str(value) for value in record.__dict__.values()) for record in caplog.records
    )
    assert injected_value not in logged
