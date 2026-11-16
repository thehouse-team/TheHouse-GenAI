"""Provider factory tests."""

from __future__ import annotations

import asyncio

import pytest

from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.base import (
    GenerativeAiProvider,
    GenerativeAiRequest,
    GuardedProvider,
    ProviderInputTooLargeError,
    ProviderTimeoutError,
)
from thehouse_genai.providers.factory import (
    SUPPORTED_PROVIDERS,
    UnsupportedProviderError,
    build_provider,
)
from thehouse_genai.providers.fake import FakeProvider


def test_supported_providers_include_fake_and_gemini() -> None:
    assert set(SUPPORTED_PROVIDERS) == {"fake", "gemini"}


def test_factory_builds_a_guarded_usable_fake_provider() -> None:
    settings = Settings(_env_file=None, genai_provider="fake")

    provider = build_provider(settings)

    assert isinstance(provider, GuardedProvider)
    assert isinstance(provider, GenerativeAiProvider)
    response = asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))
    assert response.text == "fake response"


def test_factory_rejects_missing_provider() -> None:
    settings = Settings(_env_file=None)

    with pytest.raises(UnsupportedProviderError) as exc_info:
        build_provider(settings)

    message = str(exc_info.value)
    assert "GENAI_PROVIDER is not configured" in message
    assert "fake" in message
    assert "gemini" in message


def test_factory_rejects_unsupported_provider() -> None:
    settings = Settings.model_construct(genai_provider="openai")

    with pytest.raises(UnsupportedProviderError) as exc_info:
        build_provider(settings)

    message = str(exc_info.value)
    assert "openai" in message
    assert "not available" in message
    assert "fake" in message
    assert "gemini" in message


def test_factory_requires_api_key_for_gemini() -> None:
    settings = Settings(_env_file=None, genai_provider="gemini")

    with pytest.raises(UnsupportedProviderError) as exc_info:
        build_provider(settings)

    message = str(exc_info.value)
    assert "GEMINI_API_KEY" in message
    assert "required" in message
    assert "secret" not in message.lower()


def test_factory_builds_gemini_provider_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from thehouse_genai.providers.gemini import GeminiGenerativeAiProvider

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("x-goog-api-key") == "test-key"
        assert "gemini-2.5-flash-lite" in str(request.url)
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
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
            },
        )

    transport = httpx.MockTransport(handler)
    original_init = GeminiGenerativeAiProvider.__init__

    def patched_init(
        self,
        config,
        *,
        client=None,
        endpoint_template=(
            "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        ),
    ):
        original_init(
            self,
            config,
            client=httpx.AsyncClient(transport=transport),
            endpoint_template=endpoint_template,
        )

    monkeypatch.setattr(GeminiGenerativeAiProvider, "__init__", patched_init)
    settings = Settings(_env_file=None, genai_provider="gemini", gemini_api_key="test-key")
    provider = build_provider(settings)
    response = asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))
    assert "match_score" in response.text


def test_factory_applies_the_input_limit_from_settings() -> None:
    settings = Settings(
        _env_file=None,
        genai_provider="fake",
        genai_max_input_chars=4,
    )
    provider = build_provider(settings)

    with pytest.raises(ProviderInputTooLargeError):
        asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))


def test_factory_applies_the_timeout_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    class _HangingProvider(FakeProvider):
        async def generate(self, request: GenerativeAiRequest) -> object:
            await asyncio.Event().wait()
            raise AssertionError("the provider must never answer")

    monkeypatch.setattr(
        "thehouse_genai.providers.factory.FakeProvider", _HangingProvider
    )
    settings = Settings(
        _env_file=None,
        genai_provider="fake",
        genai_timeout_seconds=0.05,
    )
    provider = build_provider(settings)

    with pytest.raises(ProviderTimeoutError):
        asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))


def test_factory_error_does_not_leak_the_api_key() -> None:
    settings = Settings(
        _env_file=None,
        genai_api_key="super-secret-key",
    )

    with pytest.raises(UnsupportedProviderError) as exc_info:
        build_provider(settings)

    message = str(exc_info.value)
    assert "super-secret-key" not in message
    assert "api_key" not in message


def test_factory_error_does_not_leak_the_api_key_for_unsupported_provider() -> None:
    settings = Settings.model_construct(
        genai_provider="unknown-provider",
        genai_api_key="super-secret-key",
    )

    with pytest.raises(UnsupportedProviderError) as exc_info:
        build_provider(settings)

    assert "super-secret-key" not in str(exc_info.value)
