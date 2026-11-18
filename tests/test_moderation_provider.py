"""Moderation port DTO, error taxonomy, guard and double tests."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from thehouse_genai.domain.moderation import (
    ModerationCategory,
    ModerationDecision,
    ModerationReason,
)
from thehouse_genai.providers.moderation import (
    FakeModerationProvider,
    GuardedModerationProvider,
    LocalRuleModerator,
    ModerationError,
    ModerationField,
    ModerationInputTooLargeError,
    ModerationInvalidResponseError,
    ModerationProvider,
    ModerationRequest,
    ModerationResponse,
    ModerationTimeoutError,
    ModerationUnavailableError,
    category_for_reasons,
)

ALL_ERRORS = (
    ModerationError,
    ModerationTimeoutError,
    ModerationUnavailableError,
    ModerationInvalidResponseError,
    ModerationInputTooLargeError,
)
SUBCLASSES = ALL_ERRORS[1:]


def _request(text: str = "Cuarto cerca de la UTTT") -> ModerationRequest:
    return ModerationRequest(text=text, field_hint=ModerationField.GENERATED_EXPLANATION)


def test_request_is_immutable() -> None:
    request = _request()

    with pytest.raises(ValidationError):
        request.text = "changed"


def test_request_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        ModerationRequest(text="hello", unknown="value")


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_request_rejects_blank_text(text: str) -> None:
    with pytest.raises(ValidationError):
        ModerationRequest(text=text)


def test_request_field_hint_is_optional_and_bounded() -> None:
    assert ModerationRequest(text="hello").field_hint is None
    assert _request().field_hint is ModerationField.GENERATED_EXPLANATION

    with pytest.raises(ValidationError):
        ModerationRequest(text="hello", field_hint="property_title")


def test_response_is_immutable() -> None:
    response = ModerationResponse(decision=ModerationDecision.ALLOW)

    with pytest.raises(ValidationError):
        response.decision = ModerationDecision.BLOCK


def test_response_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        ModerationResponse(decision=ModerationDecision.ALLOW, unknown="value")


@pytest.mark.parametrize("decision", ["allow", "review", "block"])
def test_response_accepts_the_bounded_decisions(decision: str) -> None:
    response = ModerationResponse.model_validate({"decision": decision})

    assert response.decision is ModerationDecision(decision)
    assert response.reasons == ()
    assert response.policy_version == "moderation_v1"


def test_response_rejects_unknown_reason() -> None:
    with pytest.raises(ValidationError):
        ModerationResponse.model_validate(
            {"decision": "allow", "reasons": ["NOT_A_REASON"]}
        )


def test_response_never_carries_text() -> None:
    assert "text" not in ModerationResponse.model_fields


@pytest.mark.parametrize("error_type", SUBCLASSES)
def test_error_hierarchy(error_type: type[ModerationError]) -> None:
    error = error_type()

    assert isinstance(error, ModerationError)
    assert isinstance(error, Exception)


def test_base_error_is_not_a_subclass_of_its_subclasses() -> None:
    assert not isinstance(ModerationError(), ModerationTimeoutError)


def test_errors_have_unique_codes() -> None:
    codes = [error_type.code for error_type in ALL_ERRORS]

    assert len(set(codes)) == len(codes)


@pytest.mark.parametrize(
    ("error_type", "code"),
    [
        (ModerationError, "MODERATION_ERROR"),
        (ModerationTimeoutError, "MODERATION_TIMEOUT"),
        (ModerationUnavailableError, "MODERATION_UNAVAILABLE"),
        (ModerationInvalidResponseError, "MODERATION_INVALID_RESPONSE"),
        (ModerationInputTooLargeError, "MODERATION_INPUT_TOO_LARGE"),
    ],
)
def test_error_codes_are_stable(error_type: type[ModerationError], code: str) -> None:
    assert error_type.code == code
    assert error_type().code == code


@pytest.mark.parametrize("error_type", ALL_ERRORS)
def test_error_message_is_fixed_and_detail_free(error_type: type[ModerationError]) -> None:
    first = error_type()
    second = error_type()

    assert str(first).strip()
    assert str(first) == str(second) == error_type.message
    assert error_type().args == (error_type.message,)


@pytest.mark.parametrize("error_type", ALL_ERRORS)
def test_error_does_not_accept_detail(error_type: type[ModerationError]) -> None:
    with pytest.raises(TypeError):
        raise error_type("texto que no debe filtrarse")


@pytest.mark.parametrize("error_type", ALL_ERRORS)
def test_error_never_exposes_detail(error_type: type[ModerationError]) -> None:
    error = error_type()

    assert "texto" not in str(error)
    assert "texto" not in repr(error)


def test_category_mapping_is_bounded_and_safe() -> None:
    assert category_for_reasons(
        (ModerationReason.EMAIL, ModerationReason.PHONE)
    ) == (ModerationCategory.PII,)
    assert category_for_reasons((ModerationReason.URL,)) == (ModerationCategory.URL,)
    assert category_for_reasons(
        (ModerationReason.OFFENSIVE, ModerationReason.EMAIL)
    ) == (ModerationCategory.OFFENSIVE, ModerationCategory.PII)
    assert category_for_reasons(()) == ()


def test_fake_satisfies_the_protocol() -> None:
    assert isinstance(FakeModerationProvider(), ModerationProvider)


def test_fake_returns_the_programmed_response() -> None:
    provider = FakeModerationProvider(
        decision=ModerationDecision.REVIEW,
        reasons=(ModerationReason.URL,),
    )

    response = asyncio.run(provider.check(_request()))

    assert response.decision is ModerationDecision.REVIEW
    assert response.reasons == (ModerationReason.URL,)
    assert response.policy_version == "moderation_v1"


def test_fake_is_deterministic_across_calls() -> None:
    provider = FakeModerationProvider(decision=ModerationDecision.BLOCK)

    first = asyncio.run(provider.check(_request()))
    second = asyncio.run(provider.check(_request()))

    assert first.model_dump() == second.model_dump()


def test_fake_raises_the_programmed_error() -> None:
    cause = ModerationUnavailableError()
    provider = FakeModerationProvider(error=cause)

    with pytest.raises(ModerationUnavailableError) as exc_info:
        asyncio.run(provider.check(_request()))

    assert exc_info.value is cause


def test_fake_raises_a_generic_programmed_error() -> None:
    provider = FakeModerationProvider(error=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(provider.check(_request()))


def test_fake_records_calls_and_returns_a_copy() -> None:
    provider = FakeModerationProvider()
    first = _request("primero")
    second = _request("segundo")

    asyncio.run(provider.check(first))
    asyncio.run(provider.check(second))

    assert provider.calls == [first, second]
    provider.calls.clear()
    assert len(provider.calls) == 2


def test_fake_hang_never_answers() -> None:
    provider = FakeModerationProvider(hang=True)

    async def _call() -> ModerationResponse:
        return await asyncio.wait_for(provider.check(_request()), 0.05)

    with pytest.raises(TimeoutError):
        asyncio.run(_call())


def test_local_moderator_satisfies_the_protocol() -> None:
    assert isinstance(LocalRuleModerator(), ModerationProvider)


def test_local_moderator_allows_benign_text() -> None:
    provider = LocalRuleModerator()

    response = asyncio.run(provider.check(_request("Cuesta $2,800 MXN a 1.3 km")))

    assert response.decision is ModerationDecision.ALLOW
    assert response.reasons == ()
    assert response.policy_version == "moderation_v1"


def test_local_moderator_blocks_and_reports_safe_reasons() -> None:
    provider = LocalRuleModerator()

    response = asyncio.run(provider.check(_request("Escribe a nombre@ejemplo.mx")))

    assert response.decision is ModerationDecision.BLOCK
    assert response.reasons == (ModerationReason.EMAIL,)


def test_local_moderator_does_not_record_calls() -> None:
    provider = LocalRuleModerator()

    assert not hasattr(provider, "calls")


class _WrongResponseProvider:
    """Moderator stub that violates the response contract on purpose."""

    async def check(self, request: ModerationRequest) -> object:
        return {"decision": "allow"}


def test_guard_delegates_and_returns_the_response() -> None:
    provider = FakeModerationProvider(decision=ModerationDecision.BLOCK)
    guard = GuardedModerationProvider(
        provider, timeout_seconds=1.0, max_text_chars=1_000
    )
    request = _request()

    response = asyncio.run(guard.check(request))

    assert response.decision is ModerationDecision.BLOCK
    assert provider.calls == [request]


def test_guard_rejects_oversized_text_without_calling_the_provider() -> None:
    provider = FakeModerationProvider()
    guard = GuardedModerationProvider(
        provider, timeout_seconds=1.0, max_text_chars=4
    )

    with pytest.raises(ModerationInputTooLargeError):
        asyncio.run(guard.check(_request("hello")))

    assert provider.calls == []


def test_guard_accepts_text_at_the_limit() -> None:
    provider = FakeModerationProvider()
    guard = GuardedModerationProvider(
        provider, timeout_seconds=1.0, max_text_chars=5
    )

    response = asyncio.run(guard.check(_request("hello")))

    assert response.decision is ModerationDecision.ALLOW
    assert len(provider.calls) == 1


def test_guard_converts_an_injected_timeout() -> None:
    cause = TimeoutError()
    provider = FakeModerationProvider(error=cause)
    guard = GuardedModerationProvider(
        provider, timeout_seconds=1.0, max_text_chars=1_000
    )

    with pytest.raises(ModerationTimeoutError) as exc_info:
        asyncio.run(guard.check(_request()))

    assert exc_info.value.__cause__ is cause


def test_guard_converts_a_real_timeout() -> None:
    provider = FakeModerationProvider(hang=True)
    guard = GuardedModerationProvider(
        provider, timeout_seconds=0.05, max_text_chars=1_000
    )

    with pytest.raises(ModerationTimeoutError):
        asyncio.run(guard.check(_request()))


def test_guard_propagates_a_moderation_error_unchanged() -> None:
    cause = ModerationUnavailableError()
    provider = FakeModerationProvider(error=cause)
    guard = GuardedModerationProvider(
        provider, timeout_seconds=1.0, max_text_chars=1_000
    )

    with pytest.raises(ModerationUnavailableError) as exc_info:
        asyncio.run(guard.check(_request()))

    assert exc_info.value is cause


def test_guard_normalizes_a_generic_exception() -> None:
    cause = RuntimeError("boom")
    provider = FakeModerationProvider(error=cause)
    guard = GuardedModerationProvider(
        provider, timeout_seconds=1.0, max_text_chars=1_000
    )

    with pytest.raises(ModerationUnavailableError) as exc_info:
        asyncio.run(guard.check(_request()))

    assert exc_info.value.__cause__ is cause


def test_guard_normalizes_a_validation_error() -> None:
    with pytest.raises(ValidationError) as validation:
        ModerationResponse.model_validate({"decision": "allow", "reasons": ["bad"]})
    provider = FakeModerationProvider(error=validation.value)
    guard = GuardedModerationProvider(
        provider, timeout_seconds=1.0, max_text_chars=1_000
    )

    with pytest.raises(ModerationInvalidResponseError) as exc_info:
        asyncio.run(guard.check(_request()))

    assert exc_info.value.__cause__ is validation.value


def test_guard_rejects_a_wrong_response_type() -> None:
    guard = GuardedModerationProvider(
        _WrongResponseProvider(), timeout_seconds=1.0, max_text_chars=1_000
    )

    with pytest.raises(ModerationInvalidResponseError):
        asyncio.run(guard.check(_request()))


def test_guard_does_not_capture_cancellation() -> None:
    provider = FakeModerationProvider(error=asyncio.CancelledError())
    guard = GuardedModerationProvider(
        provider, timeout_seconds=1.0, max_text_chars=1_000
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(guard.check(_request()))


def test_guard_error_never_leaks_the_text() -> None:
    provider = FakeModerationProvider(error=RuntimeError("vendor detail"))
    guard = GuardedModerationProvider(
        provider, timeout_seconds=1.0, max_text_chars=1_000
    )

    with pytest.raises(ModerationUnavailableError) as exc_info:
        asyncio.run(guard.check(_request("texto secreto unico")))

    message = str(exc_info.value)
    assert message
    assert "texto secreto unico" not in message
    assert "vendor detail" not in message


def test_guarded_moderator_satisfies_the_protocol() -> None:
    guard = GuardedModerationProvider(
        FakeModerationProvider(), timeout_seconds=1.0, max_text_chars=1_000
    )

    assert isinstance(guard, ModerationProvider)


@pytest.mark.parametrize("timeout_seconds", [0.0, -1.0])
def test_guard_rejects_an_invalid_timeout(timeout_seconds: float) -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        GuardedModerationProvider(
            FakeModerationProvider(),
            timeout_seconds=timeout_seconds,
            max_text_chars=1_000,
        )


@pytest.mark.parametrize("max_text_chars", [0, -1])
def test_guard_rejects_an_invalid_text_limit(max_text_chars: int) -> None:
    with pytest.raises(ValueError, match="max_text_chars"):
        GuardedModerationProvider(
            FakeModerationProvider(),
            timeout_seconds=1.0,
            max_text_chars=max_text_chars,
        )
