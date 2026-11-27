"""Selection of the provider implementation from validated configuration.

The factory is the second barrier: even if a `Settings` instance bypasses
validation, a provider is only built when its name is supported and, for the real
providers, when the credential and the model are present and usable.
"""

from __future__ import annotations

from typing import Final

from thehouse_genai.application.budget_port import DailyBudgetPort
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.base import GenerativeAiProvider, GuardedProvider
from thehouse_genai.providers.fake import FakeProvider
from thehouse_genai.providers.gemini import GeminiProvider
from thehouse_genai.providers.retrying import DEADLINE_MARGIN_SECONDS, RetryingProvider

SUPPORTED_PROVIDERS: Final[frozenset[str]] = frozenset({"fake", "gemini"})


class UnsupportedProviderError(ValueError):
    """Raised when the configuration requests a provider that is not available.

    This is a configuration failure, not a provider runtime failure, so it stays
    outside the `ProviderError` taxonomy.
    """


class ProviderConfigurationError(ValueError):
    """Raised when a supported provider is configured with unusable settings.

    A missing credential or model is a deployment failure, not a call failure, so
    it stays outside the `ProviderError` taxonomy, like `UnsupportedProviderError`.
    """


def _supported_names() -> str:
    """Return the supported provider names as a readable list."""

    return ", ".join(sorted(SUPPORTED_PROVIDERS))


def build_provider(
    settings: Settings,
    *,
    budget: DailyBudgetPort | None = None,
) -> GenerativeAiProvider:
    """Build the configured provider with one bounded retry, timeout and input limit.

    The retry sits inside the guard so a single call sequence is bounded by the
    configured timeout. The daily budget is shared with the use cases: they reserve
    the first attempt and the decorator reserves the retry.

    Raises:
        UnsupportedProviderError: if no provider is configured or the configured
            provider is not available in this release.
        ProviderConfigurationError: if the selected provider is missing the
            credential or the model it needs.
    """

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
    provider: GenerativeAiProvider = (
        FakeProvider() if name == "fake" else _build_gemini(settings)
    )
    provider = RetryingProvider(
        provider,
        budget=budget,
        max_total_seconds=settings.genai_timeout_seconds + DEADLINE_MARGIN_SECONDS,
    )
    return GuardedProvider(
        provider,
        timeout_seconds=settings.genai_timeout_seconds,
        max_input_chars=settings.genai_max_input_chars,
    )


def _build_gemini(settings: Settings) -> GeminiProvider:
    """Build the Gemini adapter from a validated configuration.

    The credential and the model are revalidated here, because a `Settings`
    instance may have been built without validation.

    Raises:
        ProviderConfigurationError: if the credential or the model is missing or
            unusable.
    """

    api_key = settings.genai_api_key
    model = settings.genai_model
    if api_key is None or not api_key.get_secret_value().strip():
        raise ProviderConfigurationError(
            "GENAI_API_KEY is required when GENAI_PROVIDER is 'gemini'"
        )
    if model is None or not model.strip():
        raise ProviderConfigurationError(
            "GENAI_MODEL is required when GENAI_PROVIDER is 'gemini'"
        )
    try:
        return GeminiProvider(
            api_key=api_key,
            model=model.strip(),
            timeout_seconds=settings.genai_timeout_seconds,
        )
    except ValueError as exc:
        raise ProviderConfigurationError(
            "GENAI_MODEL is not a valid Gemini model id"
        ) from exc
