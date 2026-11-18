"""Gemini safety settings contract tests.

All calls go through a `httpx.MockTransport` double: no test opens a socket.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from thehouse_genai.providers.base import (
    GenerativeAiRequest,
    ProviderInvalidResponseError,
)
from thehouse_genai.providers.gemini import GeminiProvider

API_KEY = "test-key-not-a-real-credential"
MODEL = "gemini-3.8-flash"
EXPECTED_CATEGORIES = frozenset(
    {
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
    }
)
EXPECTED_THRESHOLD = "BLOCK_MEDIUM_AND_ABOVE"


def _provider(
    handler: Callable[[httpx.Request], httpx.Response],
) -> GeminiProvider:
    """Build an adapter backed by a mock transport."""

    return GeminiProvider(
        api_key=SecretStr(API_KEY),
        model=MODEL,
        timeout_seconds=1.0,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _capture(
    payload: dict[str, Any],
) -> tuple[GeminiProvider, list[httpx.Request]]:
    """Capture the outgoing request while answering a valid vendor payload."""

    seen: list[httpx.Request] = []

    def _respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=payload)

    return _provider(_respond), seen


def _success() -> dict[str, Any]:
    return {
        "candidates": [
            {"content": {"parts": [{"text": "hola"}]}, "finishReason": "STOP"}
        ]
    }


def test_safety_settings_are_a_top_level_body_field() -> None:
    provider, seen = _capture(_success())

    asyncio.run(provider.generate(GenerativeAiRequest(prompt="hola")))

    assert len(seen) == 1
    body = json.loads(seen[0].content)
    assert "safetySettings" in body
    assert isinstance(body["safetySettings"], list)
    assert len(body["safetySettings"]) == 4


def test_safety_settings_have_exactly_the_four_categories_and_threshold() -> None:
    provider, seen = _capture(_success())

    asyncio.run(provider.generate(GenerativeAiRequest(prompt="hola")))

    settings = json.loads(seen[0].content)["safetySettings"]
    assert {item["category"] for item in settings} == EXPECTED_CATEGORIES
    assert {item["threshold"] for item in settings} == {EXPECTED_THRESHOLD}
    for item in settings:
        assert set(item) == {"category", "threshold"}
    assert "BLOCK_NONE" not in seen[0].content.decode()


def test_safety_settings_are_sent_with_every_request_shape() -> None:
    provider, seen = _capture(_success())

    request = GenerativeAiRequest(
        prompt="hola",
        system_prompt="eres un asistente",
        response_format="json",
        max_output_tokens=128,
    )
    asyncio.run(provider.generate(request))

    assert len(seen) == 1
    body = json.loads(seen[0].content)
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["systemInstruction"]["parts"][0]["text"] == "eres un asistente"
    assert len(body["safetySettings"]) == 4


@pytest.mark.parametrize(
    "payload",
    [
        {
            "candidates": [
                {
                    "content": {"parts": [{"text": "hola"}]},
                    "finishReason": "SAFETY",
                }
            ]
        },
        {"promptFeedback": {"blockReason": "SAFETY"}},
    ],
)
def test_blocked_answers_remain_invalid_responses(payload: dict[str, Any]) -> None:
    provider, seen = _capture(payload)

    with pytest.raises(ProviderInvalidResponseError):
        asyncio.run(provider.generate(GenerativeAiRequest(prompt="hola")))

    assert len(seen) == 1
    assert len(json.loads(seen[0].content)["safetySettings"]) == 4


def test_no_safety_environment_variable_is_read() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "thehouse_genai"
        / "infrastructure"
        / "config.py"
    ).read_text(encoding="utf-8")

    assert "SAFETY" not in source.upper()
