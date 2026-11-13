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
    ProviderAuthError,
    ProviderError,
    ProviderInputTooLargeError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from thehouse_genai.providers.fake import FakeProvider

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
