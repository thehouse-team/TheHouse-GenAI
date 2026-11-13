"""Selection of the provider implementation from validated configuration.

In G02 the only supported provider is the offline `FakeProvider`. The factory is the
second barrier: even if a `Settings` instance bypasses validation, no provider other
than `fake` can ever be built.
"""

from __future__ import annotations

from typing import Final

from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.base import GenerativeAiProvider, GuardedProvider
from thehouse_genai.providers.fake import FakeProvider

SUPPORTED_PROVIDERS: Final[frozenset[str]] = frozenset({"fake"})


class UnsupportedProviderError(ValueError):
    """Raised when the configuration requests a provider that is not available.

    This is a configuration failure, not a provider runtime failure, so it stays
    outside the `ProviderError` taxonomy.
    """


def _supported_names() -> str:
    """Return the supported provider names as a readable list."""

    return ", ".join(sorted(SUPPORTED_PROVIDERS))


def build_provider(settings: Settings) -> GenerativeAiProvider:
    """Build the configured provider, guarded by timeout and input limit.

    Raises:
        UnsupportedProviderError: if no provider is configured or the configured
            provider is not available in this release.
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
    return GuardedProvider(
        FakeProvider(),
        timeout_seconds=settings.genai_timeout_seconds,
        max_input_chars=settings.genai_max_input_chars,
    )
