"""Gemini adapter contract tests.

Every test runs against a `httpx.MockTransport` double: the suite never opens a
socket and never calls the vendor.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from thehouse_genai.providers.base import (
    GenerativeAiProvider,
    GenerativeAiRequest,
    ProviderInvalidResponseError,
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
