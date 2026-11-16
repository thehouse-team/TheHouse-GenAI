"""Gemini API adapter: the concrete provider behind the vendor-neutral port.

The adapter speaks the Gemini REST API directly with `httpx`, so the service keeps a
single HTTP dependency and no vendor SDK. Everything vendor specific lives in this
module: the port, its DTOs and the error taxonomy stay untouched.

This is the only module of the service allowed to import `httpx`, and the only one
that may open a socket. The test suite never reaches the network: the client is
injected with a `httpx.MockTransport` double.

Failures are normalized at the edge of the adapter: the HTTP status, the transport
errors and the payload validation all become errors of the own taxonomy, without the
vendor body, the headers or the credential ever reaching a message or a log line.
"""

from __future__ import annotations

import logging
import re
from time import perf_counter
from typing import Any, Final

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from thehouse_genai.providers.base import (
    GenerativeAiRequest,
    GenerativeAiResponse,
    GenerativeAiUsage,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

_PROVIDER_NAME: Final[str] = "gemini"
_API_BASE_URL: Final[str] = "https://generativelanguage.googleapis.com"
_API_VERSION: Final[str] = "v1beta"
_API_KEY_HEADER: Final[str] = "x-goog-api-key"
_JSON_MIME_TYPE: Final[str] = "application/json"
_MODEL_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# Finish reasons that mean the content was withheld. They are failures of the
# contract, not empty answers.
_BLOCKED_FINISH_REASONS: Final[frozenset[str]] = frozenset(
    {
        "SAFETY",
        "PROHIBITED_CONTENT",
        "BLOCKLIST",
        "RECITATION",
        "SPII",
        "IMAGE_SAFETY",
        "ESCALATION",
        "LANGUAGE",
    }
)


class _GeminiModel(BaseModel):
    """Base model for the vendor payload: unknown fields are ignored."""

    model_config = ConfigDict(extra="ignore")


class _GeminiPart(_GeminiModel):
    """A single part of a candidate content."""

    text: str | None = None


class _GeminiContent(_GeminiModel):
    """The content produced by the model."""

    parts: list[_GeminiPart] = Field(default_factory=list)


class _GeminiCandidate(_GeminiModel):
    """One candidate answer of the vendor."""

    content: _GeminiContent | None = None
    finishReason: str | None = None


class _GeminiUsage(_GeminiModel):
    """Token accounting reported by the vendor."""

    promptTokenCount: int = 0
    candidatesTokenCount: int = 0


class _GeminiFeedback(_GeminiModel):
    """Feedback about the prompt, reported when no candidate is returned."""

    blockReason: str | None = None


class _GeminiPayload(_GeminiModel):
    """The `generateContent` response, reduced to the fields the port needs."""

    candidates: list[_GeminiCandidate] = Field(default_factory=list)
    usageMetadata: _GeminiUsage | None = None
    promptFeedback: _GeminiFeedback | None = None
    modelVersion: str | None = None


def _elapsed_ms(started: float) -> float:
    """Return the milliseconds elapsed since the given mark."""

    return round((perf_counter() - started) * 1000, 2)


def _has_deprecation_header(response: httpx.Response) -> bool:
    """Report whether the vendor sent a deprecation warning.

    Only the presence is used: neither the header name nor its value is logged,
    because a log line never carries vendor headers.
    """

    return any("deprecat" in name.lower() for name in response.headers)


class GeminiProvider:
    """Call the Gemini `generateContent` endpoint behind the provider port.

    The credential is held as a `SecretStr` and travels only in the
    `x-goog-api-key` header, never in the URL or in the body.
    """

    def __init__(
        self,
        *,
        api_key: SecretStr,
        model: str,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Bind the credential, the model and the transport.

        The client is optional: without it the provider creates one per call, so
        there is no connection pool and no lifecycle to close. Tests inject a
        client backed by a `httpx.MockTransport`.

        Raises:
            ValueError: if the model id is invalid or the timeout is not positive.
        """

        if not _MODEL_ID_PATTERN.fullmatch(model):
            raise ValueError("model must be a valid Gemini model id")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = client

    def __repr__(self) -> str:
        """Represent the provider without exposing the credential."""

        return f"GeminiProvider(model={self._model!r})"

    async def generate(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        """Ask the vendor for a completion and normalize the answer.

        Raises:
            ProviderError: any normalized provider failure.
        """

        started = perf_counter()
        error: ProviderError
        try:
            response = await self._post(request)
            self._raise_for_status(response.status_code)
            result = self._parse_response(response)
        except httpx.TimeoutException as exc:
            error = ProviderTimeoutError()
            self._log_failure(request, started, error)
            raise error from exc
        except httpx.HTTPError as exc:
            error = ProviderUnavailableError()
            self._log_failure(request, started, error)
            raise error from exc
        except ProviderError as exc:
            self._log_failure(request, started, exc)
            raise
        self._log_success(request, started, result)
        if _has_deprecation_header(response):
            logger.warning(
                "provider.call.deprecation",
                extra={
                    "provider": _PROVIDER_NAME,
                    "provider_model": result.provider_model,
                },
            )
        return result

    async def _post(self, request: GenerativeAiRequest) -> httpx.Response:
        """Send the mapped request to the vendor and return the raw response."""

        url = f"{_API_BASE_URL}/{_API_VERSION}/models/{self._model}:generateContent"
        headers = {_API_KEY_HEADER: self._api_key.get_secret_value()}
        payload = self._build_payload(request)
        if self._client is not None:
            return await self._client.post(url, headers=headers, json=payload)
        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(url, headers=headers, json=payload)

    def _raise_for_status(self, status_code: int) -> None:
        """Map an HTTP status to the provider error taxonomy.

        The status is inspected before the body is parsed, so an error page is
        never read and never reaches an exception.

        Raises:
            ProviderError: for any status outside the 2xx range.
        """

        if status_code < 400:
            return
        if status_code in (401, 403):
            raise ProviderAuthError()
        if status_code == 408:
            raise ProviderTimeoutError()
        if status_code == 429:
            raise ProviderRateLimitError()
        if status_code < 500:
            raise ProviderInvalidResponseError()
        raise ProviderUnavailableError()

    def _build_payload(self, request: GenerativeAiRequest) -> dict[str, Any]:
        """Map the neutral request to the vendor body."""

        config: dict[str, Any] = {"temperature": request.temperature}
        if request.max_output_tokens is not None:
            config["maxOutputTokens"] = request.max_output_tokens
        if request.response_format == "json":
            config["responseMimeType"] = _JSON_MIME_TYPE
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": config,
        }
        if request.system_prompt is not None:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}
        return payload

    def _parse_response(self, response: httpx.Response) -> GenerativeAiResponse:
        """Validate the vendor payload and normalize it to the port DTO.

        Raises:
            ProviderInvalidResponseError: if the payload does not satisfy the port.
        """

        try:
            payload = _GeminiPayload.model_validate(response.json())
        except ValueError as exc:  # pydantic ValidationError is a ValueError
            raise ProviderInvalidResponseError() from exc
        if payload.promptFeedback is not None and payload.promptFeedback.blockReason:
            raise ProviderInvalidResponseError()
        if not payload.candidates:
            raise ProviderInvalidResponseError()
        candidate = payload.candidates[0]
        if candidate.finishReason in _BLOCKED_FINISH_REASONS:
            raise ProviderInvalidResponseError()
        text = self._extract_text(candidate)
        if not text:
            raise ProviderInvalidResponseError()
        usage = payload.usageMetadata if payload.usageMetadata is not None else _GeminiUsage()
        return GenerativeAiResponse(
            text=text,
            usage=GenerativeAiUsage(
                input_tokens=usage.promptTokenCount,
                output_tokens=usage.candidatesTokenCount,
            ),
            finish_reason=candidate.finishReason,
            provider_model=payload.modelVersion or self._model,
        )

    def _extract_text(self, candidate: _GeminiCandidate) -> str:
        """Join the text parts of a candidate."""

        if candidate.content is None:
            return ""
        return "".join(part.text for part in candidate.content.parts if part.text)

    def _log_success(
        self,
        request: GenerativeAiRequest,
        started: float,
        response: GenerativeAiResponse,
    ) -> None:
        """Record the call metadata: never the prompt nor the answer."""

        logger.info(
            "provider.call.completed",
            extra={
                "provider": _PROVIDER_NAME,
                "provider_model": response.provider_model,
                "duration_ms": _elapsed_ms(started),
                "prompt_chars": len(request.prompt),
                "completion_chars": len(response.text),
            },
        )

    def _log_failure(
        self,
        request: GenerativeAiRequest,
        started: float,
        error: ProviderError,
    ) -> None:
        """Record the failure metadata: never the vendor detail nor the credential."""

        logger.warning(
            "provider.call.failed",
            extra={
                "provider": _PROVIDER_NAME,
                "error_code": error.code,
                "duration_ms": _elapsed_ms(started),
                "prompt_chars": len(request.prompt),
            },
        )
