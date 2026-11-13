"""Deterministic in-memory provider used as a test double.

The double never touches the network, never waits on real time and never generates
random identifiers, so every assertion over it is reproducible.
"""

from __future__ import annotations

import asyncio

from thehouse_genai.providers.base import (
    GenerativeAiRequest,
    GenerativeAiResponse,
    GenerativeAiUsage,
)

_CHARS_PER_TOKEN = 4


def _estimate_tokens(chars: int) -> int:
    """Estimate tokens deterministically from a character count."""

    return (chars + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN


class FakeProvider:
    """Offline provider double with programmable success, failure and timeout.

    The recorded requests are kept in memory only: `calls` is never logged and never
    serialized. When both `error` and `hang` are set, the error takes precedence.
    """

    def __init__(
        self,
        *,
        text: str = "fake response",
        usage: GenerativeAiUsage | None = None,
        error: BaseException | None = None,
        hang: bool = False,
    ) -> None:
        self._text = text
        self._usage = usage
        self._error = error
        self._hang = hang
        self._calls: list[GenerativeAiRequest] = []

    @property
    def calls(self) -> list[GenerativeAiRequest]:
        """Copy of the requests received, in order (test-only inspection)."""

        return list(self._calls)

    async def generate(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        """Return the programmed response, or fail as programmed.

        Raises:
            BaseException: the programmed error, when one was configured.
        """

        self._calls.append(request)
        if self._error is not None:
            raise self._error
        if self._hang:
            await asyncio.Event().wait()
        return GenerativeAiResponse(
            text=self._text,
            usage=self._usage or self._derive_usage(request),
        )

    def _derive_usage(self, request: GenerativeAiRequest) -> GenerativeAiUsage:
        """Derive token counts from the input and output lengths."""

        input_chars = len(request.prompt) + len(request.system_prompt or "")
        return GenerativeAiUsage(
            input_tokens=_estimate_tokens(input_chars),
            output_tokens=_estimate_tokens(len(self._text)),
        )
