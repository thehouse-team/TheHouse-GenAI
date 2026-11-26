"""Gemini adapter contract tests.

Every test runs against a `httpx.MockTransport` double: the suite never opens a
socket and never calls the vendor.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from thehouse_genai.infrastructure.logging import JsonFormatter
from thehouse_genai.providers.base import (
    GenerativeAiProvider,
    GenerativeAiRequest,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from thehouse_genai.providers.gemini import GeminiProvider

API_KEY = "test-key-not-a-real-credential"
MODEL = "gemini-3.8-flash"
EXPECTED_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def _success_payload(
    *,
    text: str = "hola",
    finish_reason: str = "STOP",
    model_version: str = "gemini-3.8-flash-2026-01-01",
    prompt_tokens: int = 11,
    candidates_tokens: int = 7,
) -> dict[str, Any]:
    """Build a valid `generateContent` response."""

    return {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": text}]},
                "finishReason": finish_reason,
                "index": 0,
            }
        ],
        "usageMetadata": {
            "promptTokenCount": prompt_tokens,
            "candidatesTokenCount": candidates_tokens,
            "totalTokenCount": prompt_tokens + candidates_tokens,
        },
        "modelVersion": model_version,
    }


def _handler(
    payload: Any,
    *,
    status_code: int = 200,
) -> Callable[[httpx.Request], httpx.Response]:
    """Return a transport handler that always answers the same payload."""

    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return _respond


def _provider(
    handler: Callable[[httpx.Request], httpx.Response],
    **overrides: Any,
) -> GeminiProvider:
    """Build a provider backed by a mock transport."""

    kwargs: dict[str, Any] = {
        "api_key": SecretStr(API_KEY),
        "model": MODEL,
        "timeout_seconds": 1.0,
        "client": httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    }
    kwargs.update(overrides)
    return GeminiProvider(**kwargs)


def _generate(
    provider: GeminiProvider,
    request: GenerativeAiRequest,
) -> Any:
    """Run one generation through the provider."""

    return asyncio.run(provider.generate(request))


def _logged_text(caplog: pytest.LogCaptureFixture) -> str:
    """Render every captured record, including its structured fields."""

    return "\n".join(
        " ".join(str(value) for value in record.__dict__.values())
        for record in caplog.records
    )


def test_provider_satisfies_the_port_protocol() -> None:
    provider = _provider(_handler(_success_payload()))

    assert isinstance(provider, GenerativeAiProvider)


def test_request_targets_the_generate_content_endpoint() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_success_payload())

    provider = _provider(_respond)
    _generate(provider, GenerativeAiRequest(prompt="hola"))

    assert len(seen) == 1
    assert seen[0].method == "POST"
    assert str(seen[0].url) == EXPECTED_URL


def test_credential_travels_only_in_the_header() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_success_payload())

    provider = _provider(_respond)
    _generate(provider, GenerativeAiRequest(prompt="hola"))

    request = seen[0]
    assert request.headers["x-goog-api-key"] == API_KEY
    assert API_KEY not in str(request.url)
    assert "key=" not in str(request.url)
    assert API_KEY not in request.content.decode()
    assert request.headers["content-type"] == "application/json"


def test_body_maps_the_prompt() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_success_payload())

    provider = _provider(_respond)
    _generate(provider, GenerativeAiRequest(prompt="explica esto"))

    body = seen[0].read()
    assert b'"contents"' in body
    assert b"explica esto" in body


def test_body_omits_the_system_instruction_when_absent() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_success_payload())

    provider = _provider(_respond)
    _generate(provider, GenerativeAiRequest(prompt="hola"))

    assert b"systemInstruction" not in seen[0].read()


def test_body_maps_the_system_prompt() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_success_payload())

    provider = _provider(_respond)
    request = GenerativeAiRequest(prompt="hola", system_prompt="eres un asistente")
    _generate(provider, request)

    body = seen[0].read()
    assert b"systemInstruction" in body
    assert b"eres un asistente" in body


def test_body_requests_json_when_the_format_is_json() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_success_payload())

    provider = _provider(_respond)
    request = GenerativeAiRequest(prompt="hola", response_format="json")
    _generate(provider, request)

    assert b'"responseMimeType":"application/json"' in seen[0].read()


def test_body_omits_the_response_mime_type_for_text() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_success_payload())

    provider = _provider(_respond)
    _generate(provider, GenerativeAiRequest(prompt="hola", response_format="text"))

    assert b"responseMimeType" not in seen[0].read()


def test_body_omits_the_max_output_tokens_when_absent() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_success_payload())

    provider = _provider(_respond)
    _generate(provider, GenerativeAiRequest(prompt="hola"))

    assert b"maxOutputTokens" not in seen[0].read()


def test_body_maps_the_max_output_tokens() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_success_payload())

    provider = _provider(_respond)
    request = GenerativeAiRequest(prompt="hola", max_output_tokens=512)
    _generate(provider, request)

    assert b'"maxOutputTokens":512' in seen[0].read()


def test_body_always_maps_the_temperature() -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_success_payload())

    provider = _provider(_respond)
    request = GenerativeAiRequest(prompt="hola", temperature=0.7)
    _generate(provider, request)

    assert b'"temperature":0.7' in seen[0].read()


def test_response_maps_text_usage_and_finish_reason() -> None:
    provider = _provider(_handler(_success_payload(text="hola", finish_reason="STOP")))

    response = _generate(provider, GenerativeAiRequest(prompt="hola"))

    assert response.text == "hola"
    assert response.finish_reason == "STOP"
    assert response.usage.input_tokens == 11
    assert response.usage.output_tokens == 7
    assert response.usage.total_tokens == 18


def test_response_maps_the_provider_model_from_the_vendor() -> None:
    provider = _provider(_handler(_success_payload(model_version="gemini-3.8-flash-2026-01-01")))

    response = _generate(provider, GenerativeAiRequest(prompt="hola"))

    assert response.provider_model == "gemini-3.8-flash-2026-01-01"


def test_response_falls_back_to_the_configured_model() -> None:
    provider = _provider(_handler({"candidates": [{"content": {"parts": [{"text": "hola"}]}}]}))

    response = _generate(provider, GenerativeAiRequest(prompt="hola"))

    assert response.provider_model == MODEL


def test_response_joins_every_text_part() -> None:
    payload = {
        "candidates": [
            {
                "content": {"parts": [{"text": "parte "}, {"text": "una"}]},
                "finishReason": "STOP",
            }
        ]
    }
    provider = _provider(_handler(payload))

    response = _generate(provider, GenerativeAiRequest(prompt="hola"))

    assert response.text == "parte una"


def test_response_defaults_the_usage_when_it_is_absent() -> None:
    payload = {"candidates": [{"content": {"parts": [{"text": "hola"}]}, "finishReason": "STOP"}]}
    provider = _provider(_handler(payload))

    response = _generate(provider, GenerativeAiRequest(prompt="hola"))

    assert response.usage.input_tokens == 0
    assert response.usage.output_tokens == 0


def test_truncated_answer_is_not_an_error() -> None:
    provider = _provider(_handler(_success_payload(text="corta", finish_reason="MAX_TOKENS")))

    response = _generate(provider, GenerativeAiRequest(prompt="hola"))

    assert response.text == "corta"
    assert response.finish_reason == "MAX_TOKENS"


def test_blocked_prompt_is_an_invalid_response() -> None:
    payload = {"promptFeedback": {"blockReason": "SAFETY"}}
    provider = _provider(_handler(payload))

    with pytest.raises(ProviderInvalidResponseError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


def test_missing_candidates_is_an_invalid_response() -> None:
    provider = _provider(_handler({"candidates": []}))

    with pytest.raises(ProviderInvalidResponseError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


def test_absent_candidates_is_an_invalid_response() -> None:
    provider = _provider(_handler({}))

    with pytest.raises(ProviderInvalidResponseError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


@pytest.mark.parametrize(
    "finish_reason",
    ["SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "RECITATION", "SPII"],
)
def test_blocked_finish_reason_is_an_invalid_response(finish_reason: str) -> None:
    payload = {
        "candidates": [
            {
                "content": {"parts": [{"text": "hola"}]},
                "finishReason": finish_reason,
            }
        ]
    }
    provider = _provider(_handler(payload))

    with pytest.raises(ProviderInvalidResponseError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


def test_empty_text_is_an_invalid_response() -> None:
    provider = _provider(_handler(_success_payload(text="")))

    with pytest.raises(ProviderInvalidResponseError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


def test_missing_content_is_an_invalid_response() -> None:
    provider = _provider(_handler({"candidates": [{"finishReason": "STOP"}]}))

    with pytest.raises(ProviderInvalidResponseError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


def test_unparseable_body_is_an_invalid_response() -> None:
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    provider = _provider(_respond)

    with pytest.raises(ProviderInvalidResponseError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


def test_unexpected_body_shape_is_an_invalid_response() -> None:
    provider = _provider(_handler(["not", "an", "object"]))

    with pytest.raises(ProviderInvalidResponseError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


@pytest.mark.parametrize(
    "model",
    ["", " ", "gemini 3.8 flash", "gemini/3.8", "gemini?x=1", "a" * 65, "-leading-dash"],
)
def test_invalid_model_id_is_rejected(model: str) -> None:
    with pytest.raises(ValueError, match="model"):
        GeminiProvider(
            api_key=SecretStr(API_KEY),
            model=model,
            timeout_seconds=1.0,
        )


def test_invalid_timeout_is_rejected() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        GeminiProvider(
            api_key=SecretStr(API_KEY),
            model=MODEL,
            timeout_seconds=0.0,
        )


def test_repr_does_not_expose_the_credential() -> None:
    provider = _provider(_handler(_success_payload()))

    assert API_KEY not in repr(provider)
    assert MODEL in repr(provider)


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (400, ProviderInvalidResponseError),
        (404, ProviderInvalidResponseError),
        (418, ProviderInvalidResponseError),
        (401, ProviderAuthError),
        (403, ProviderAuthError),
        (408, ProviderTimeoutError),
        (429, ProviderRateLimitError),
        (500, ProviderUnavailableError),
        (502, ProviderUnavailableError),
        (503, ProviderUnavailableError),
    ],
)
def test_http_status_is_mapped_to_the_taxonomy(
    status_code: int,
    error_type: type[ProviderError],
) -> None:
    provider = _provider(_handler({"error": {"message": "vendor-detail"}}, status_code=status_code))

    with pytest.raises(error_type):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


def test_timeout_is_mapped_to_the_timeout_error() -> None:
    def _respond(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("vendor timeout")

    provider = _provider(_respond)

    with pytest.raises(ProviderTimeoutError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


def test_network_error_is_mapped_to_unavailable() -> None:
    def _respond(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(_respond)

    with pytest.raises(ProviderUnavailableError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))


def test_vendor_body_never_reaches_the_exception() -> None:
    provider = _provider(_handler({"error": {"message": "vendor-detail-secret"}}, status_code=400))

    with pytest.raises(ProviderInvalidResponseError) as exc_info:
        _generate(provider, GenerativeAiRequest(prompt="hola"))

    assert "vendor-detail-secret" not in str(exc_info.value)
    assert "vendor-detail-secret" not in repr(exc_info.value)


def test_credential_never_reaches_the_exception_chain() -> None:
    def _respond(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("vendor timeout")

    provider = _provider(_respond)

    with pytest.raises(ProviderTimeoutError) as exc_info:
        _generate(provider, GenerativeAiRequest(prompt="hola"))

    cause = exc_info.value.__cause__
    assert cause is not None
    assert API_KEY not in str(exc_info.value)
    assert API_KEY not in str(cause)


def test_success_log_records_metadata_without_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    provider = _provider(_handler(_success_payload(text="respuesta completa")))

    _generate(provider, GenerativeAiRequest(prompt="mi prompt secreto"))

    record = caplog.records[-1]
    assert record.getMessage() == "provider.call.completed"
    assert record.provider == "gemini"
    assert record.provider_model == "gemini-3.8-flash-2026-01-01"
    assert record.prompt_chars == len("mi prompt secreto")
    assert record.completion_chars == len("respuesta completa")
    assert record.duration_ms >= 0
    assert not hasattr(record, "http_status")
    assert not hasattr(record, "transport_error")

    logged = _logged_text(caplog)
    assert "mi prompt secreto" not in logged
    assert "respuesta completa" not in logged
    assert API_KEY not in logged


def test_failure_log_records_the_error_code_without_detail(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    provider = _provider(_handler({"error": {"message": "vendor-detail-secret"}}, status_code=429))

    with pytest.raises(ProviderRateLimitError):
        _generate(provider, GenerativeAiRequest(prompt="mi prompt secreto"))

    record = caplog.records[-1]
    assert record.getMessage() == "provider.call.failed"
    assert record.provider == "gemini"
    assert record.error_code == "PROVIDER_RATE_LIMIT"
    assert record.http_status == 429
    assert not hasattr(record, "transport_error")

    logged = _logged_text(caplog)
    assert "vendor-detail-secret" not in logged
    assert "mi prompt secreto" not in logged
    assert API_KEY not in logged


def test_timeout_log_records_the_error_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)

    def _respond(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("vendor timeout")

    provider = _provider(_respond)

    with pytest.raises(ProviderTimeoutError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))

    record = caplog.records[-1]
    assert record.error_code == "PROVIDER_TIMEOUT"
    assert record.transport_error == "ReadTimeout"
    assert not hasattr(record, "http_status")

    logged = _logged_text(caplog)
    assert "vendor timeout" not in logged


def test_transport_failure_logs_only_the_exception_class(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)

    def _respond(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("secret-host.invalid refused the connection")

    provider = _provider(_respond)

    with pytest.raises(ProviderUnavailableError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))

    record = caplog.records[-1]
    assert record.getMessage() == "provider.call.failed"
    assert record.error_code == "PROVIDER_UNAVAILABLE"
    assert record.transport_error == "ConnectError"
    assert not hasattr(record, "http_status")

    logged = _logged_text(caplog)
    assert "secret-host.invalid" not in logged
    assert "refused the connection" not in logged


def test_invalid_payload_logs_the_received_status(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    provider = _provider(_handler({"candidates": []}))

    with pytest.raises(ProviderInvalidResponseError):
        _generate(provider, GenerativeAiRequest(prompt="hola"))

    record = caplog.records[-1]
    assert record.error_code == "PROVIDER_INVALID_RESPONSE"
    assert record.http_status == 200


def test_deprecation_header_is_signalled_without_logging_the_header(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)

    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_success_payload(),
            headers={"x-deprecation-warning": "use the new model"},
        )

    provider = _provider(_respond)
    _generate(provider, GenerativeAiRequest(prompt="hola"))

    messages = [record.getMessage() for record in caplog.records]
    assert "provider.call.deprecation" in messages

    logged = _logged_text(caplog)
    assert "x-deprecation-warning" not in logged
    assert "use the new model" not in logged


def test_json_logging_emits_the_provider_metadata() -> None:
    record = logging.LogRecord(
        name="thehouse_genai.providers.gemini",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="provider.call.completed",
        args=(),
        exc_info=None,
    )
    record.provider = "gemini"
    record.provider_model = "gemini-3.8-flash"
    record.prompt_chars = 12
    record.completion_chars = 4
    record.duration_ms = 1.5

    payload = json.loads(JsonFormatter().format(record))

    assert payload["provider"] == "gemini"
    assert payload["provider_model"] == "gemini-3.8-flash"
    assert payload["prompt_chars"] == 12
    assert payload["completion_chars"] == 4
    assert payload["duration_ms"] == 1.5
