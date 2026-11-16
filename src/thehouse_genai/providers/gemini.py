"""Gemini Developer API provider adapter (text generation, no SDK)."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

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


@dataclass(frozen=True)
class GeminiProviderConfig:
    """Immutable configuration for the Gemini adapter."""

    api_key: str
    model: str
    timeout_seconds: float
    max_output_tokens: int
    max_retries: int = 0


class GeminiGenerativeAiProvider:
    """Generate text via Gemini REST API behind the neutral provider port."""

    def __init__(
        self,
        config: GeminiProviderConfig,
        *,
        client: httpx.AsyncClient | None = None,
        endpoint_template: str = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    ) -> None:
        self._config = config
        self._client = client
        self._endpoint_template = endpoint_template

    async def generate(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        last_error: ProviderError | None = None
        attempts = self._config.max_retries + 1
        for attempt in range(attempts):
            try:
                return await self._generate_once(request)
            except ProviderRateLimitError as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    raise
                await asyncio.sleep(min(0.05 * (attempt + 1), 0.15))
            except ProviderUnavailableError as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    raise
                await asyncio.sleep(min(0.05 * (attempt + 1), 0.15))
        if last_error is not None:
            raise last_error
        raise ProviderUnavailableError()

    async def _generate_once(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        payload = self._build_payload(request)
        url = self._endpoint_template.format(model=self._config.model)
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._config.api_key,
        }
        try:
            if self._client is not None:
                response = await self._client.post(url, json=payload, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
                    response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError() from exc

        if response.status_code == 200:
            return self._parse_response(response)
        if response.status_code in {401, 403}:
            raise ProviderAuthError()
        if response.status_code == 429:
            raise ProviderRateLimitError()
        if response.status_code in {400, 404, 422}:
            raise ProviderInvalidResponseError()
        if 500 <= response.status_code <= 599:
            raise ProviderUnavailableError()
        raise ProviderUnavailableError()

    def _build_payload(self, request: GenerativeAiRequest) -> dict[str, Any]:
        generation_config: dict[str, Any] = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_output_tokens or self._config.max_output_tokens,
        }
        if request.response_format == "json":
            generation_config["responseMimeType"] = "application/json"
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": generation_config,
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}
        return payload

    def _parse_response(self, response: httpx.Response) -> GenerativeAiResponse:
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProviderInvalidResponseError() from exc
        if not isinstance(data, dict):
            raise ProviderInvalidResponseError()

        block_reason = self._extract_block_reason(data)
        if block_reason:
            raise ProviderInvalidResponseError()

        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ProviderInvalidResponseError()
        first = candidates[0]
        if not isinstance(first, dict):
            raise ProviderInvalidResponseError()
        finish_reason = first.get("finishReason")
        allowed_reasons = {"STOP", "MAX_TOKENS", "FINISH_REASON_UNSPECIFIED"}
        if isinstance(finish_reason, str) and finish_reason not in allowed_reasons:
            raise ProviderInvalidResponseError()

        content = first.get("content")
        if not isinstance(content, dict):
            raise ProviderInvalidResponseError()
        parts = content.get("parts")
        if not isinstance(parts, list) or not parts:
            raise ProviderInvalidResponseError()
        texts: list[str] = []
        for part in parts:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    texts.append(text)
        combined = "\n".join(t for t in texts if t.strip()).strip()
        if not combined:
            raise ProviderInvalidResponseError()

        usage_meta = data.get("usageMetadata")
        input_tokens = 0
        output_tokens = 0
        if isinstance(usage_meta, dict):
            pt = usage_meta.get("promptTokenCount")
            ct = usage_meta.get("candidatesTokenCount")
            if isinstance(pt, int) and pt >= 0:
                input_tokens = pt
            if isinstance(ct, int) and ct >= 0:
                output_tokens = ct
        usage = GenerativeAiUsage(input_tokens=input_tokens, output_tokens=output_tokens)

        try:
            return GenerativeAiResponse(
                text=combined,
                usage=usage,
                finish_reason=str(finish_reason) if finish_reason is not None else None,
                provider_model=self._config.model,
            )
        except ValidationError as exc:
            raise ProviderInvalidResponseError() from exc

    @staticmethod
    def _extract_block_reason(data: dict[str, Any]) -> str | None:
        feedback = data.get("promptFeedback")
        if isinstance(feedback, dict):
            reason = feedback.get("blockReason")
            if isinstance(reason, str) and reason and reason != "BLOCK_REASON_UNSPECIFIED":
                return reason
        return None
