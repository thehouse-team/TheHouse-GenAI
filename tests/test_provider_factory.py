"""Provider factory tests."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

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
    ProviderConfigurationError,
    UnsupportedProviderError,
    build_provider,
)
from thehouse_genai.providers.fake import FakeProvider
from thehouse_genai.providers.gemini import GeminiProvider

GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_PAYLOAD = {
    "candidates": [
        {"content": {"parts": [{"text": "hola"}]}, "finishReason": "STOP"},
    ]
}


def _gemini_settings(**overrides: Any) -> Settings:
    """Build a valid gemini configuration."""

    values: dict[str, Any] = {
        "genai_provider": "gemini",
        "genai_api_key": "test-key",
        "genai_model": GEMINI_MODEL,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _mock_gemini_transport(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    """Make the factory build a Gemini adapter backed by a mock transport."""

    class _MockedGemini(GeminiProvider):
        def __init__(self, **kwargs: Any) -> None:
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            super().__init__(client=client, **kwargs)

    monkeypatch.setattr("thehouse_genai.providers.factory.GeminiProvider", _MockedGemini)


def test_supported_providers_are_fake_and_gemini() -> None:
    assert set(SUPPORTED_PROVIDERS) == {"fake", "gemini"}


def test_factory_builds_a_guarded_usable_provider() -> None:
    settings = Settings(_env_file=None, genai_provider="fake")

    provider = build_provider(settings)

    assert isinstance(provider, GuardedProvider)
    assert isinstance(provider, GenerativeAiProvider)
    response = asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))
    assert response.text == "fake response"


def test_factory_builds_a_guarded_gemini_provider() -> None:
    provider = build_provider(_gemini_settings())

    assert isinstance(provider, GuardedProvider)
    assert isinstance(provider, GenerativeAiProvider)


def test_factory_rejects_missing_provider() -> None:
    settings = Settings(_env_file=None)

    with pytest.raises(UnsupportedProviderError) as exc_info:
        build_provider(settings)

    assert str(exc_info.value) == "GENAI_PROVIDER is not configured; supported: fake, gemini"


def test_factory_rejects_unsupported_provider() -> None:
    settings = Settings.model_construct(genai_provider="openai")

    with pytest.raises(UnsupportedProviderError) as exc_info:
        build_provider(settings)

    message = str(exc_info.value)
    assert "openai" in message
    assert "fake" in message
    assert "gemini" in message
    assert "not available" in message


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
        genai_provider="openai",
        genai_api_key="super-secret-key",
    )

    with pytest.raises(UnsupportedProviderError) as exc_info:
        build_provider(settings)

    assert "super-secret-key" not in str(exc_info.value)


def test_factory_rejects_gemini_without_api_key() -> None:
    settings = Settings.model_construct(
        genai_provider="gemini",
        genai_api_key=None,
        genai_model=GEMINI_MODEL,
    )

    with pytest.raises(ProviderConfigurationError) as exc_info:
        build_provider(settings)

    assert "GENAI_API_KEY" in str(exc_info.value)


def test_factory_rejects_gemini_with_a_blank_api_key() -> None:
    settings = Settings.model_construct(
        genai_provider="gemini",
        genai_api_key=SecretStr("   "),
        genai_model=GEMINI_MODEL,
    )

    with pytest.raises(ProviderConfigurationError) as exc_info:
        build_provider(settings)

    assert "GENAI_API_KEY" in str(exc_info.value)


def test_factory_rejects_gemini_without_model() -> None:
    settings = Settings.model_construct(
        genai_provider="gemini",
        genai_api_key=SecretStr("test-key"),
        genai_model=None,
    )

    with pytest.raises(ProviderConfigurationError) as exc_info:
        build_provider(settings)

    assert "GENAI_MODEL" in str(exc_info.value)


def test_factory_rejects_gemini_with_an_invalid_model_id() -> None:
    settings = Settings.model_construct(
        genai_provider="gemini",
        genai_api_key=SecretStr("test-key"),
        genai_model="gemini 3.8 flash",
    )

    with pytest.raises(ProviderConfigurationError) as exc_info:
        build_provider(settings)

    assert "GENAI_MODEL" in str(exc_info.value)


def test_factory_error_does_not_leak_the_api_key_for_gemini() -> None:
    settings = Settings.model_construct(
        genai_provider="gemini",
        genai_api_key=SecretStr("super-secret-key"),
        genai_model=None,
    )

    with pytest.raises(ProviderConfigurationError) as exc_info:
        build_provider(settings)

    message = str(exc_info.value)
    assert "super-secret-key" not in message
    assert "GENAI_MODEL" in message


def test_factory_gemini_calls_the_vendor_through_the_mock_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=GEMINI_PAYLOAD)

    _mock_gemini_transport(monkeypatch, _respond)
    provider = build_provider(_gemini_settings())

    response = asyncio.run(provider.generate(GenerativeAiRequest(prompt="hola")))

    assert response.text == "hola"
    assert response.finish_reason == "STOP"


def test_factory_applies_the_input_limit_for_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=GEMINI_PAYLOAD)

    _mock_gemini_transport(monkeypatch, _respond)
    provider = build_provider(_gemini_settings(genai_max_input_chars=4))

    with pytest.raises(ProviderInputTooLargeError):
        asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))

    assert seen == []


def test_factory_applies_the_timeout_for_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _hang(request: httpx.Request) -> httpx.Response:
        await asyncio.Event().wait()
        raise AssertionError("the provider must never answer")

    _mock_gemini_transport(monkeypatch, _hang)
    provider = build_provider(_gemini_settings(genai_timeout_seconds=0.05))

    with pytest.raises(ProviderTimeoutError):
        asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))
