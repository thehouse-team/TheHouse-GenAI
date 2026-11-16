"""Gemini API adapter: the concrete provider behind the vendor-neutral port.

The adapter speaks the Gemini REST API directly with `httpx`, so the service keeps a
single HTTP dependency and no vendor SDK. Everything vendor specific lives in this
module: the port, its DTOs and the error taxonomy stay untouched.

This is the only module of the service allowed to import `httpx`, and the only one
that may open a socket. The test suite never reaches the network: the client is
injected with a `httpx.MockTransport` double.

This block covers the request and response mapping. The HTTP status, timeout and
network mapping, together with the internal logging, land with the error handling
block of the same spec.
"""

from __future__ import annotations

import re
from typing import Any, Final

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from thehouse_genai.providers.base import (
    GenerativeAiRequest,
    GenerativeAiResponse,
    GenerativeAiUsage,
    ProviderInvalidResponseError,
)

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
            ProviderInvalidResponseError: if the payload does not satisfy the port.
        """

        url = f"{_API_BASE_URL}/{_API_VERSION}/models/{self._model}:generateContent"
        headers = {_API_KEY_HEADER: self._api_key.get_secret_value()}
        payload = self._build_payload(request)
        if self._client is not None:
            response = await self._client.post(url, headers=headers, json=payload)
        else:
            timeout = httpx.Timeout(self._timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
        return self._parse_response(response)

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
