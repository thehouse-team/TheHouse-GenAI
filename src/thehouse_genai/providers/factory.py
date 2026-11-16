"""Selection of the provider implementation from validated configuration."""

from __future__ import annotations

from typing import Final

from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.base import GenerativeAiProvider, GuardedProvider
from thehouse_genai.providers.fake import FakeProvider
from thehouse_genai.providers.gemini import GeminiGenerativeAiProvider, GeminiProviderConfig

SUPPORTED_PROVIDERS: Final[frozenset[str]] = frozenset({"fake", "gemini"})


class UnsupportedProviderError(ValueError):
    """Raised when the configuration requests a provider that is not available."""


def _supported_names() -> str:
    return ", ".join(sorted(SUPPORTED_PROVIDERS))


def build_provider(settings: Settings) -> GenerativeAiProvider:
    """Build the configured provider, guarded by timeout and input limit."""

    name = settings.genai_provider
    if name is None:
        raise UnsupportedProviderError(
            f"GENAI_PROVIDER is not configured; supported: {_supported_names()}"
        )
    if name not in SUPPORTED_PROVIDERS:
        raise UnsupportedProviderError(
            f"provider {name!r} is not available in this release; "
            f"supported: {_supported_names()}"
        )

    if name == "fake":
        provider: GenerativeAiProvider = FakeProvider()
    elif name == "gemini":
        api_key = settings.resolved_api_key()
        if api_key is None:
            raise UnsupportedProviderError(
                "GEMINI_API_KEY (or GENAI_API_KEY) is required when GENAI_PROVIDER=gemini"
            )
        provider = GeminiGenerativeAiProvider(
            GeminiProviderConfig(
                api_key=api_key.get_secret_value(),
                model=settings.resolved_model(),
                timeout_seconds=settings.genai_timeout_seconds,
                max_output_tokens=settings.genai_max_output_tokens,
                max_retries=settings.genai_max_retries,
            )
        )
    else:
        raise UnsupportedProviderError(
            f"provider {name!r} is not available in this release; "
            f"supported: {_supported_names()}"
        )

    return GuardedProvider(
        provider,
        timeout_seconds=settings.genai_timeout_seconds,
        max_input_chars=settings.genai_max_input_chars,
    )
