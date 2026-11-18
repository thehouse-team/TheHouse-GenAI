"""Vendor-neutral moderation port: immutable DTOs, errors and local implementations.

The port is independent of any provider: the offline `LocalRuleModerator` delegates to
the versioned domain policy, and the fake is a deterministic test double. There is no
HTTP client and no network call in this module. The central guard applies the input
limit and the timeout to every implementation, in the same way as the LLM port.
"""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Any, ClassVar, Final, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from thehouse_genai.domain.moderation import (
    POLICY_VERSION,
    ModerationCategory,
    ModerationDecision,
    ModerationReason,
    classify,
)


class ModerationField(StrEnum):
    """Bounded hints describing where the text came from."""

    GENERATED_EXPLANATION = "generated_explanation"


class _ModerationModel(BaseModel):
    """Base model for port DTOs: frozen and closed to unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModerationRequest(_ModerationModel):
    """The only request shape accepted by the moderation port."""

    text: str = Field(min_length=1)
    field_hint: ModerationField | None = None

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        """Reject text that carries no content."""

        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class ModerationResponse(_ModerationModel):
    """Decision and stable reason codes; never the moderated text itself."""

    decision: ModerationDecision
    reasons: tuple[ModerationReason, ...] = ()
    policy_version: str = POLICY_VERSION


class ModerationError(Exception):
    """Base class for normalized moderation failures.

    Like `ProviderError`, the constructor takes no free-form detail, so moderated text
    or a vendor payload can never leak into an exception or a log line.
    """

    code: ClassVar[str] = "MODERATION_ERROR"
    message: ClassVar[str] = "The moderation check failed."

    def __init__(self) -> None:
        super().__init__(self.message)

    def __reduce__(self) -> tuple[type[ModerationError], tuple[Any, ...]]:
        """Keep the exception picklable despite the detail-free constructor."""

        return (type(self), ())


class ModerationTimeoutError(ModerationError):
    """The moderator did not answer within the configured timeout."""

    code = "MODERATION_TIMEOUT"
    message = "The moderator did not answer within the configured timeout."


class ModerationUnavailableError(ModerationError):
    """The moderator could not complete the check."""

    code = "MODERATION_UNAVAILABLE"
    message = "The moderator is unavailable."


class ModerationInvalidResponseError(ModerationError):
    """The moderator returned a value that violates the port contract."""

    code = "MODERATION_INVALID_RESPONSE"
    message = "The moderator returned a response that does not satisfy the contract."


class ModerationInputTooLargeError(ModerationError):
    """The text exceeds the configured limit and was never checked."""

    code = "MODERATION_INPUT_TOO_LARGE"
    message = "The text exceeds the configured maximum size and was not checked."


@runtime_checkable
class ModerationProvider(Protocol):
    """Vendor-neutral moderation port."""

    async def check(self, request: ModerationRequest) -> ModerationResponse:
        """Classify the text and return a bounded decision.

        Raises:
            ModerationError: any normalized moderation failure.
        """

        ...


_REASON_CATEGORY: Final = {
    ModerationReason.EMAIL: ModerationCategory.PII,
    ModerationReason.PHONE: ModerationCategory.PII,
    ModerationReason.URL: ModerationCategory.URL,
    ModerationReason.OFFENSIVE: ModerationCategory.OFFENSIVE,
}


def category_for_reasons(
    reasons: tuple[ModerationReason, ...],
) -> tuple[ModerationCategory, ...]:
    """Map reason codes to bounded categories for safe log metadata."""

    categories = {_REASON_CATEGORY[reason] for reason in reasons}
    return tuple(sorted(categories, key=lambda category: category.value))


class GuardedModerationProvider:
    """Enforce the text limit and the timeout around a moderation implementation."""

    def __init__(
        self,
        provider: ModerationProvider,
        *,
        timeout_seconds: float,
        max_text_chars: int,
    ) -> None:
        """Bind the delegate and the limits.

        Raises:
            ValueError: if the timeout or the text limit is not positive.
        """

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        if max_text_chars < 1:
            raise ValueError("max_text_chars must be at least 1")
        self._provider = provider
        self._timeout_seconds = timeout_seconds
        self._max_text_chars = max_text_chars

    async def check(self, request: ModerationRequest) -> ModerationResponse:
        """Validate the input, delegate under a timeout and normalize the outcome."""

        self._validate_input_size(request)
        try:
            raw: object = await asyncio.wait_for(
                self._provider.check(request),
                self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise ModerationTimeoutError() from exc
        except ModerationError:
            raise
        except ValidationError as exc:
            raise ModerationInvalidResponseError() from exc
        except Exception as exc:
            raise ModerationUnavailableError() from exc
        if not isinstance(raw, ModerationResponse):
            raise ModerationInvalidResponseError()
        return raw

    def _validate_input_size(self, request: ModerationRequest) -> None:
        """Reject oversized text before the moderator is ever invoked."""

        if len(request.text) > self._max_text_chars:
            raise ModerationInputTooLargeError()


class FakeModerationProvider:
    """Offline moderation double with programmable decision, error and timeout."""

    def __init__(
        self,
        *,
        decision: ModerationDecision = ModerationDecision.ALLOW,
        reasons: tuple[ModerationReason, ...] = (),
        error: BaseException | None = None,
        hang: bool = False,
        policy_version: str = POLICY_VERSION,
    ) -> None:
        """Program the next response; error takes precedence over hang."""

        self._decision = decision
        self._reasons = reasons
        self._error = error
        self._hang = hang
        self._policy_version = policy_version
        self._calls: list[ModerationRequest] = []

    @property
    def calls(self) -> list[ModerationRequest]:
        """Copy of the requests received, in order (test-only inspection)."""

        return list(self._calls)

    async def check(self, request: ModerationRequest) -> ModerationResponse:
        """Return the programmed response, or fail as programmed."""

        self._calls.append(request)
        if self._error is not None:
            raise self._error
        if self._hang:
            await asyncio.Event().wait()
        return ModerationResponse(
            decision=self._decision,
            reasons=self._reasons,
            policy_version=self._policy_version,
        )


class LocalRuleModerator:
    """Offline moderator that delegates to the versioned domain policy."""

    async def check(self, request: ModerationRequest) -> ModerationResponse:
        """Classify the text with deterministic local rules, without a network call."""

        verdict = classify(request.text)
        return ModerationResponse(
            decision=verdict.decision,
            reasons=verdict.reasons,
            policy_version=verdict.policy_version,
        )
