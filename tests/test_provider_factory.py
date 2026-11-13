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


def test_supported_providers_is_only_fake() -> None:
    assert set(SUPPORTED_PROVIDERS) == {"fake"}


def test_factory_builds_a_guarded_usable_provider() -> None:
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

    assert str(exc_info.value) == "GENAI_PROVIDER is not configured; supported: fake"


def test_factory_rejects_unsupported_provider() -> None:
    settings = Settings.model_construct(genai_provider="gemini")

    with pytest.raises(UnsupportedProviderError) as exc_info:
        build_provider(settings)

    message = str(exc_info.value)
    assert "gemini" in message
    assert "fake" in message
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
        genai_provider="gemini",
        genai_api_key="super-secret-key",
    )

    with pytest.raises(UnsupportedProviderError) as exc_info:
        build_provider(settings)

    assert "super-secret-key" not in str(exc_info.value)
