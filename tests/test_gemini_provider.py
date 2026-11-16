"""Gemini provider adapter tests (no network)."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from thehouse_genai.providers.base import (
    GenerativeAiRequest,
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from thehouse_genai.providers.gemini import GeminiGenerativeAiProvider, GeminiProviderConfig


def _run(coro):
    return asyncio.run(coro)


def _provider(handler: httpx.MockTransport | httpx.BaseTransport) -> GeminiGenerativeAiProvider:
    client = httpx.AsyncClient(transport=handler)
    return GeminiGenerativeAiProvider(
        GeminiProviderConfig(
            api_key="test-key",
            model="gemini-2.5-flash-lite",
            timeout_seconds=5.0,
            max_output_tokens=128,
            max_retries=0,
        ),
        client=client,
    )


def test_gemini_success_parses_json_text_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("x-goog-api-key") == "test-key"
        body = json.loads(request.content.decode())
        assert body["contents"][0]["parts"][0]["text"] == "hola"
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"explanation":"ok",'
                                        '"facts_used":["match_score"]}'
                                    )
                                }
                            ]
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 4},
            },
        )

    provider = _provider(httpx.MockTransport(handler))
    resp = _run(
        provider.generate(
            GenerativeAiRequest(prompt="hola", system_prompt="sys", response_format="json")
        )
    )
    assert resp.text.startswith("{")
    assert resp.usage.input_tokens == 3
    assert resp.usage.output_tokens == 4
    assert resp.provider_model == "gemini-2.5-flash-lite"


@pytest.mark.parametrize(
    "status,exc",
    [(401, ProviderAuthError), (403, ProviderAuthError), (429, ProviderRateLimitError)],
)
def test_gemini_maps_auth_and_rate_limit(status: int, exc: type[Exception]) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "secret"}})

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(exc):
        _run(provider.generate(GenerativeAiRequest(prompt="hola")))


def test_gemini_maps_server_error() -> None:
    provider = _provider(httpx.MockTransport(lambda _: httpx.Response(503, json={"error": {}})))
    with pytest.raises(ProviderUnavailableError):
        _run(provider.generate(GenerativeAiRequest(prompt="hola")))


def test_gemini_rejects_invalid_json() -> None:
    provider = _provider(httpx.MockTransport(lambda _: httpx.Response(200, text="not-json")))
    with pytest.raises(ProviderInvalidResponseError):
        _run(provider.generate(GenerativeAiRequest(prompt="hola")))


def test_gemini_rejects_empty_candidates() -> None:
    provider = _provider(
        httpx.MockTransport(lambda _: httpx.Response(200, json={"candidates": []}))
    )
    with pytest.raises(ProviderInvalidResponseError):
        _run(provider.generate(GenerativeAiRequest(prompt="hola")))


def test_gemini_rejects_safety_block() -> None:
    provider = _provider(
        httpx.MockTransport(
            lambda _: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})
        )
    )
    with pytest.raises(ProviderInvalidResponseError):
        _run(provider.generate(GenerativeAiRequest(prompt="hola")))


def test_gemini_timeout_maps_to_provider_timeout() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=httpx.Request("POST", "https://example.test"))

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(ProviderTimeoutError):
        _run(provider.generate(GenerativeAiRequest(prompt="hola")))


def test_gemini_retries_on_transient_unavailable_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={})
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "ok"}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GeminiGenerativeAiProvider(
        GeminiProviderConfig(
            api_key="k",
            model="gemini-2.5-flash-lite",
            timeout_seconds=5,
            max_output_tokens=64,
            max_retries=1,
        ),
        client=client,
    )
    resp = _run(provider.generate(GenerativeAiRequest(prompt="hola")))
    assert resp.text == "ok"
    assert calls["n"] == 2


def test_gemini_does_not_leak_key_or_raw_error_in_exception_message() -> None:
    provider = _provider(
        httpx.MockTransport(lambda _: httpx.Response(500, text="super-secret-key"))
    )
    with pytest.raises(ProviderUnavailableError) as exc_info:
        _run(provider.generate(GenerativeAiRequest(prompt="hola")))
    assert "super-secret-key" not in str(exc_info.value)
    assert "test-key" not in str(exc_info.value)
