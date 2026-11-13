"""Vendor-neutral LLM port: immutable DTOs and the provider error taxonomy.

This module owns the contract shared by every provider implementation. It must stay
free of SDK types, HTTP payloads and vendor specifics so that the application layer
never depends on a provider. The concrete adapter for a real provider arrives with
spec 011, behind this same port.
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class _ProviderModel(BaseModel):
    """Base model for port DTOs: frozen and closed to unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class GenerativeAiUsage(_ProviderModel):
    """Token accounting reported by the provider."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed, derived from the reported counters."""

        return self.input_tokens + self.output_tokens


class GenerativeAiRequest(_ProviderModel):
    """Vendor-neutral request; the only shape the port accepts.

    The maximum input size is not part of the model: it comes from
    `GENAI_MAX_INPUT_CHARS` and is enforced by the port guard before any call.
    """

    prompt: str = Field(min_length=1)
    system_prompt: str | None = None
    response_format: Literal["text", "json"] = "text"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, ge=1, le=8192)

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        """Reject prompts that carry no content."""

        if not value.strip():
            raise ValueError("prompt must not be blank")
        return value

    @field_validator("system_prompt")
    @classmethod
    def _system_prompt_not_blank(cls, value: str | None) -> str | None:
        """Reject a blank system prompt; an absent one stays absent."""

        if value is not None and not value.strip():
            raise ValueError("system_prompt must not be blank")
        return value


class GenerativeAiResponse(_ProviderModel):
    """Vendor-neutral response.

    `provider_model` is internal metadata: it may be recorded in internal logs but
    must never reach an API response, because the model is not part of the contract
    with TheHouse Backend.
    """

    text: str = Field(min_length=1)
    usage: GenerativeAiUsage
    finish_reason: str | None = None
    provider_model: str | None = None


class ProviderError(Exception):
    """Base class for normalized provider failures.

    The constructor takes no free-form detail, so a vendor payload, a prompt or a
    credential can never leak into an exception. Every class carries a stable `code`
    and a fixed, safe message.
    """

    code: ClassVar[str] = "PROVIDER_ERROR"
    retryable: ClassVar[bool] = False
    message: ClassVar[str] = "The provider call failed."

    def __init__(self) -> None:
        super().__init__(self.message)

    def __reduce__(self) -> tuple[type[ProviderError], tuple[Any, ...]]:
        """Keep the exception picklable despite the detail-free constructor."""

        return (type(self), ())


class ProviderTimeoutError(ProviderError):
    """The provider did not answer within the configured timeout."""

    code = "PROVIDER_TIMEOUT"
    retryable = True
    message = "The provider did not answer within the configured timeout."


class ProviderAuthError(ProviderError):
    """The provider rejected the credentials of the request."""

    code = "PROVIDER_AUTH"
    retryable = False
    message = "The provider rejected the provided credentials."


class ProviderRateLimitError(ProviderError):
    """The provider rejected the request because of rate limiting."""

    code = "PROVIDER_RATE_LIMIT"
    retryable = True
    message = "The provider rejected the request due to rate limiting."


class ProviderUnavailableError(ProviderError):
    """The provider could not serve the request."""

    code = "PROVIDER_UNAVAILABLE"
    retryable = True
    message = "The provider is unavailable."


class ProviderInvalidResponseError(ProviderError):
    """The provider answered with a payload that violates the port contract."""

    code = "PROVIDER_INVALID_RESPONSE"
    retryable = False
    message = "The provider returned a response that does not satisfy the contract."


class ProviderInputTooLargeError(ProviderError):
    """The input exceeds the configured maximum size and was never sent."""

    code = "PROVIDER_INPUT_TOO_LARGE"
    retryable = False
    message = "The input exceeds the configured maximum size and was not sent."


@runtime_checkable
class GenerativeAiProvider(Protocol):
    """Vendor-neutral LLM port.

    Implementations never expose SDK types, HTTP payloads or vendor errors to
    callers: every failure is reported as a `ProviderError`. The timeout is not part
    of this signature; the port guard applies it to every call.
    """

    async def generate(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        """Produce a completion for the given request.

        Raises:
            ProviderError: any normalized provider failure.
        """

        ...


class GuardedProvider:
    """Enforce the input limit and the timeout around a provider implementation.

    The guard is the only place that measures the input and that bounds a call in
    time, so every provider, current or future, inherits the same guarantees. It
    never logs and never exposes the request content or vendor details.
    """

    def __init__(
        self,
        provider: GenerativeAiProvider,
        *,
        timeout_seconds: float,
        max_input_chars: int,
    ) -> None:
        """Bind the delegate and the limits.

        Raises:
            ValueError: if the timeout is not positive or the input limit is invalid.
        """

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        if max_input_chars < 1:
            raise ValueError("max_input_chars must be at least 1")
        self._provider = provider
        self._timeout_seconds = timeout_seconds
        self._max_input_chars = max_input_chars

    async def generate(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        """Validate the input, delegate under a timeout and normalize the outcome.

        Raises:
            ProviderError: any normalized provider failure.
        """

        self._validate_input_size(request)
        try:
            raw: object = await asyncio.wait_for(
                self._provider.generate(request),
                self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise ProviderTimeoutError() from exc
        except ProviderError:
            raise
        except ValidationError as exc:
            raise ProviderInvalidResponseError() from exc
        except Exception as exc:
            raise ProviderUnavailableError() from exc
        if not isinstance(raw, GenerativeAiResponse):
            raise ProviderInvalidResponseError()
        return raw

    def _validate_input_size(self, request: GenerativeAiRequest) -> None:
        """Reject oversized input before the provider is ever invoked."""

        size = len(request.prompt) + len(request.system_prompt or "")
        if size > self._max_input_chars:
            raise ProviderInputTooLargeError()
