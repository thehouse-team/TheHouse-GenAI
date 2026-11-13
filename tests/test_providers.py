"""Provider port DTO and error taxonomy tests."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from thehouse_genai.providers.base import (
    GenerativeAiProvider,
    GenerativeAiRequest,
    GenerativeAiResponse,
    GenerativeAiUsage,
    GuardedProvider,
    ProviderAuthError,
    ProviderError,
    ProviderInputTooLargeError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from thehouse_genai.providers.fake import FakeProvider


class _WrongResponseProvider:
    """Provider stub that violates the response contract on purpose."""

    async def generate(self, request: GenerativeAiRequest) -> object:
        return {"text": "not a dto"}

ALL_ERRORS = (
    ProviderError,
    ProviderTimeoutError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    ProviderInvalidResponseError,
    ProviderInputTooLargeError,
)

SUBCLASSES = ALL_ERRORS[1:]


def test_request_is_immutable() -> None:
    request = GenerativeAiRequest(prompt="hello")

    with pytest.raises(ValidationError):
        request.prompt = "changed"


def test_request_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        GenerativeAiRequest(prompt="hello", unknown="value")


@pytest.mark.parametrize("prompt", ["", "   ", "\n\t "])
def test_request_rejects_blank_prompt(prompt: str) -> None:
    with pytest.raises(ValidationError):
        GenerativeAiRequest(prompt=prompt)


def test_request_rejects_blank_system_prompt() -> None:
    with pytest.raises(ValidationError):
        GenerativeAiRequest(prompt="hello", system_prompt="   ")


def test_request_accepts_absent_system_prompt() -> None:
    request = GenerativeAiRequest(prompt="hello")

    assert request.system_prompt is None


def test_request_defaults() -> None:
    request = GenerativeAiRequest(prompt="hello")

    assert request.response_format == "text"
    assert request.temperature == 0.2
    assert request.max_output_tokens is None


@pytest.mark.parametrize("temperature", [-0.1, 2.1])
def test_request_rejects_invalid_temperature(temperature: float) -> None:
    with pytest.raises(ValidationError):
        GenerativeAiRequest(prompt="hello", temperature=temperature)


@pytest.mark.parametrize("temperature", [0.0, 2.0])
def test_request_accepts_temperature_bounds(temperature: float) -> None:
    assert GenerativeAiRequest(prompt="hello", temperature=temperature).temperature == temperature


@pytest.mark.parametrize("max_output_tokens", [0, -1, 8193])
def test_request_rejects_invalid_max_output_tokens(max_output_tokens: int) -> None:
    with pytest.raises(ValidationError):
        GenerativeAiRequest(prompt="hello", max_output_tokens=max_output_tokens)


@pytest.mark.parametrize("max_output_tokens", [1, 8192])
def test_request_accepts_max_output_tokens_bounds(max_output_tokens: int) -> None:
    request = GenerativeAiRequest(prompt="hello", max_output_tokens=max_output_tokens)

    assert request.max_output_tokens == max_output_tokens


@pytest.mark.parametrize("response_format", ["text", "json"])
def test_request_accepts_supported_response_formats(response_format: str) -> None:
    request = GenerativeAiRequest(prompt="hello", response_format=response_format)

    assert request.response_format == response_format


def test_request_rejects_unsupported_response_format() -> None:
    with pytest.raises(ValidationError):
        GenerativeAiRequest(prompt="hello", response_format="xml")


def test_response_is_immutable() -> None:
    response = GenerativeAiResponse(
        text="hello",
        usage=GenerativeAiUsage(input_tokens=1, output_tokens=2),
    )

    with pytest.raises(ValidationError):
        response.text = "changed"


def test_response_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        GenerativeAiResponse(
            text="hello",
            usage=GenerativeAiUsage(input_tokens=1, output_tokens=2),
            unknown="value",
        )


def test_response_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        GenerativeAiResponse(
            text="",
            usage=GenerativeAiUsage(input_tokens=1, output_tokens=2),
        )


def test_response_accepts_optional_metadata() -> None:
    response = GenerativeAiResponse(
        text="hello",
        usage=GenerativeAiUsage(input_tokens=1, output_tokens=2),
        finish_reason="stop",
        provider_model="internal-model",
    )

    assert response.finish_reason == "stop"
    assert response.provider_model == "internal-model"


def test_usage_is_immutable() -> None:
    usage = GenerativeAiUsage(input_tokens=1, output_tokens=2)

    with pytest.raises(ValidationError):
        usage.input_tokens = 5


def test_usage_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        GenerativeAiUsage(input_tokens=1, output_tokens=2, unknown="value")


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens"),
    [(-1, 0), (0, -1)],
)
def test_usage_rejects_negative_tokens(input_tokens: int, output_tokens: int) -> None:
    with pytest.raises(ValidationError):
        GenerativeAiUsage(input_tokens=input_tokens, output_tokens=output_tokens)


def test_usage_accepts_zero_tokens() -> None:
    usage = GenerativeAiUsage(input_tokens=0, output_tokens=0)

    assert usage.total_tokens == 0


def test_usage_total_is_derived() -> None:
    usage = GenerativeAiUsage(input_tokens=7, output_tokens=13)

    assert usage.total_tokens == 20


@pytest.mark.parametrize("error_type", SUBCLASSES)
def test_error_hierarchy(error_type: type[ProviderError]) -> None:
    error = error_type()

    assert isinstance(error, ProviderError)
    assert isinstance(error, Exception)


def test_base_error_is_not_a_subclass_of_its_subclasses() -> None:
    assert not isinstance(ProviderError(), ProviderTimeoutError)


def test_errors_have_unique_codes() -> None:
    codes = [error_type.code for error_type in ALL_ERRORS]

    assert len(set(codes)) == len(codes)


@pytest.mark.parametrize(
    ("error_type", "code"),
    [
        (ProviderError, "PROVIDER_ERROR"),
        (ProviderTimeoutError, "PROVIDER_TIMEOUT"),
        (ProviderAuthError, "PROVIDER_AUTH"),
        (ProviderRateLimitError, "PROVIDER_RATE_LIMIT"),
        (ProviderUnavailableError, "PROVIDER_UNAVAILABLE"),
        (ProviderInvalidResponseError, "PROVIDER_INVALID_RESPONSE"),
        (ProviderInputTooLargeError, "PROVIDER_INPUT_TOO_LARGE"),
    ],
)
def test_error_codes_are_stable(error_type: type[ProviderError], code: str) -> None:
    assert error_type.code == code
    assert error_type().code == code


@pytest.mark.parametrize(
    ("error_type", "retryable"),
    [
        (ProviderError, False),
        (ProviderTimeoutError, True),
        (ProviderAuthError, False),
        (ProviderRateLimitError, True),
        (ProviderUnavailableError, True),
        (ProviderInvalidResponseError, False),
        (ProviderInputTooLargeError, False),
    ],
)
def test_error_retryable_flags(error_type: type[ProviderError], retryable: bool) -> None:
    assert error_type.retryable is retryable
    assert error_type().retryable is retryable


@pytest.mark.parametrize("error_type", ALL_ERRORS)
def test_error_message_is_fixed_and_not_empty(error_type: type[ProviderError]) -> None:
    first = error_type()
    second = error_type()

    assert str(first).strip()
    assert str(first) == str(second) == error_type.message


@pytest.mark.parametrize("error_type", ALL_ERRORS)
def test_error_does_not_accept_detail_argument(error_type: type[ProviderError]) -> None:
    with pytest.raises(TypeError):
        raise error_type("vendor payload with a secret key")


@pytest.mark.parametrize("error_type", ALL_ERRORS)
def test_error_never_exposes_detail(error_type: type[ProviderError]) -> None:
    error = error_type()

    assert "vendor" not in str(error)
    assert "secret" not in repr(error)
    assert error.args == (error_type.message,)


def test_fake_provider_satisfies_protocol() -> None:
    assert isinstance(FakeProvider(), GenerativeAiProvider)


def test_fake_returns_programmed_response() -> None:
    provider = FakeProvider(text="programmed")

    response = asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))

    assert isinstance(response, GenerativeAiResponse)
    assert response.text == "programmed"


def test_fake_is_deterministic_across_calls() -> None:
    provider = FakeProvider(text="programmed")
    request = GenerativeAiRequest(prompt="hello")

    first = asyncio.run(provider.generate(request))
    second = asyncio.run(provider.generate(request))

    assert first.model_dump() == second.model_dump()


def test_fake_raises_programmed_taxonomy_error() -> None:
    provider = FakeProvider(error=ProviderAuthError())

    with pytest.raises(ProviderAuthError):
        asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))


def test_fake_raises_programmed_generic_error() -> None:
    provider = FakeProvider(error=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))


def test_fake_records_calls() -> None:
    provider = FakeProvider()
    first = GenerativeAiRequest(prompt="first")
    second = GenerativeAiRequest(prompt="second")

    asyncio.run(provider.generate(first))
    asyncio.run(provider.generate(second))

    assert provider.calls == [first, second]


def test_fake_calls_returns_a_copy() -> None:
    provider = FakeProvider()
    asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))

    provider.calls.clear()

    assert len(provider.calls) == 1


def test_fake_derives_usage_from_lengths() -> None:
    provider = FakeProvider(text="ok")
    request = GenerativeAiRequest(prompt="hello")

    response = asyncio.run(provider.generate(request))

    assert response.usage.input_tokens == 2
    assert response.usage.output_tokens == 1
    assert response.usage.total_tokens == 3


def test_fake_derives_usage_including_system_prompt() -> None:
    provider = FakeProvider(text="ok")
    request = GenerativeAiRequest(prompt="hello", system_prompt="abcd")

    response = asyncio.run(provider.generate(request))

    assert response.usage.input_tokens == 3


def test_fake_uses_explicit_usage() -> None:
    usage = GenerativeAiUsage(input_tokens=10, output_tokens=5)
    provider = FakeProvider(text="ok", usage=usage)

    response = asyncio.run(provider.generate(GenerativeAiRequest(prompt="hello")))

    assert response.usage == usage


def test_fake_hang_never_answers() -> None:
    provider = FakeProvider(hang=True)
    request = GenerativeAiRequest(prompt="hello")

    async def _call() -> GenerativeAiResponse:
        return await asyncio.wait_for(provider.generate(request), 0.05)

    with pytest.raises(TimeoutError):
        asyncio.run(_call())


def test_guard_delegates_and_returns_response() -> None:
    provider = FakeProvider(text="ok")
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=1_000)
    request = GenerativeAiRequest(prompt="hello")

    response = asyncio.run(guard.generate(request))

    assert response.text == "ok"
    assert provider.calls == [request]


def test_guard_rejects_oversized_input_without_calling_provider() -> None:
    provider = FakeProvider()
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=4)

    with pytest.raises(ProviderInputTooLargeError):
        asyncio.run(guard.generate(GenerativeAiRequest(prompt="hello")))

    assert provider.calls == []


def test_guard_accepts_input_at_the_limit() -> None:
    provider = FakeProvider()
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=5)

    response = asyncio.run(guard.generate(GenerativeAiRequest(prompt="hello")))

    assert response.text == "fake response"
    assert len(provider.calls) == 1


def test_guard_counts_system_prompt_in_the_limit() -> None:
    provider = FakeProvider()
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=8)
    request = GenerativeAiRequest(prompt="hello", system_prompt="abcd")

    with pytest.raises(ProviderInputTooLargeError):
        asyncio.run(guard.generate(request))

    assert provider.calls == []


def test_guard_accepts_system_prompt_at_the_limit() -> None:
    provider = FakeProvider()
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=9)
    request = GenerativeAiRequest(prompt="hello", system_prompt="abcd")

    asyncio.run(guard.generate(request))

    assert len(provider.calls) == 1


def test_guard_converts_injected_timeout_error() -> None:
    cause = TimeoutError()
    provider = FakeProvider(error=cause)
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=1_000)

    with pytest.raises(ProviderTimeoutError) as exc_info:
        asyncio.run(guard.generate(GenerativeAiRequest(prompt="hello")))

    assert exc_info.value.__cause__ is cause


def test_guard_converts_real_timeout() -> None:
    provider = FakeProvider(hang=True)
    guard = GuardedProvider(provider, timeout_seconds=0.05, max_input_chars=1_000)

    with pytest.raises(ProviderTimeoutError):
        asyncio.run(guard.generate(GenerativeAiRequest(prompt="hello")))


def test_guard_propagates_provider_error_unchanged() -> None:
    cause = ProviderAuthError()
    provider = FakeProvider(error=cause)
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=1_000)

    with pytest.raises(ProviderAuthError) as exc_info:
        asyncio.run(guard.generate(GenerativeAiRequest(prompt="hello")))

    assert exc_info.value is cause


def test_guard_normalizes_generic_exception() -> None:
    cause = RuntimeError("boom")
    provider = FakeProvider(error=cause)
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=1_000)

    with pytest.raises(ProviderUnavailableError) as exc_info:
        asyncio.run(guard.generate(GenerativeAiRequest(prompt="hello")))

    assert exc_info.value.__cause__ is cause


def test_guard_normalizes_validation_error() -> None:
    with pytest.raises(ValidationError) as validation:
        GenerativeAiResponse.model_validate({"text": ""})
    provider = FakeProvider(error=validation.value)
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=1_000)

    with pytest.raises(ProviderInvalidResponseError) as exc_info:
        asyncio.run(guard.generate(GenerativeAiRequest(prompt="hello")))

    assert exc_info.value.__cause__ is validation.value


def test_guard_rejects_wrong_response_type() -> None:
    guard = GuardedProvider(
        _WrongResponseProvider(), timeout_seconds=1.0, max_input_chars=1_000
    )

    with pytest.raises(ProviderInvalidResponseError):
        asyncio.run(guard.generate(GenerativeAiRequest(prompt="hello")))


def test_guard_does_not_capture_cancellation() -> None:
    provider = FakeProvider(error=asyncio.CancelledError())
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=1_000)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(guard.generate(GenerativeAiRequest(prompt="hello")))


def test_guard_error_does_not_leak_prompt_or_vendor_detail() -> None:
    provider = FakeProvider(error=RuntimeError("vendor secret"))
    guard = GuardedProvider(provider, timeout_seconds=1.0, max_input_chars=1_000)

    with pytest.raises(ProviderUnavailableError) as exc_info:
        asyncio.run(guard.generate(GenerativeAiRequest(prompt="mi prompt secreto")))

    message = str(exc_info.value)
    assert message
    assert "mi prompt secreto" not in message
    assert "vendor secret" not in message


def test_guarded_provider_satisfies_protocol() -> None:
    guard = GuardedProvider(FakeProvider(), timeout_seconds=1.0, max_input_chars=1_000)

    assert isinstance(guard, GenerativeAiProvider)


@pytest.mark.parametrize("timeout_seconds", [0.0, -1.0])
def test_guard_rejects_invalid_timeout(timeout_seconds: float) -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        GuardedProvider(FakeProvider(), timeout_seconds=timeout_seconds, max_input_chars=1_000)


@pytest.mark.parametrize("max_input_chars", [0, -1])
def test_guard_rejects_invalid_input_limit(max_input_chars: int) -> None:
    with pytest.raises(ValueError, match="max_input_chars"):
        GuardedProvider(FakeProvider(), timeout_seconds=1.0, max_input_chars=max_input_chars)
