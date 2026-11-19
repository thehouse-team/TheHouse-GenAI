"""End-to-end moderation checks for parse-search with fictitious lexicon terms.

The shipped lexicon is never opened or quoted here: like the 006 tests, a lexicon made
only of invented tokens replaces the loader for the duration of each test. Every call
goes through offline doubles, so no test reaches the network.
"""

from __future__ import annotations

import asyncio
import json
import logging

import pytest

from thehouse_genai.application.parse_search import ParseSearch
from thehouse_genai.domain import moderation
from thehouse_genai.domain.moderation import Lexicon
from thehouse_genai.domain.search_filters import (
    ParseSearchRequest,
    SearchConfidence,
    empty_filters,
)
from thehouse_genai.providers.fake import FakeProvider
from thehouse_genai.providers.moderation import FakeModerationProvider, LocalRuleModerator

_BLOCK_TERM = "zorbaflux"
_REVIEW_TERM = "plimbo"


def _fictitious_lexicon() -> Lexicon:
    """Build a lexicon made only of invented tokens."""

    return Lexicon(
        version="test",
        block=frozenset({_BLOCK_TERM}),
        review=frozenset({_REVIEW_TERM}),
        allowlist=frozenset(),
    )


def _patch_lexicon(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the on-disk lexicon with an in-memory one for one test."""

    monkeypatch.setattr(moderation, "load_lexicon", lambda: _fictitious_lexicon())


def _request(query: str) -> ParseSearchRequest:
    return ParseSearchRequest.model_validate({"query": query})


def _completion() -> str:
    """A valid completion with grounded filters, so only moderation can reject it."""

    return json.dumps(
        {
            "filters": {
                "maxBudget": 3000,
                "currency": "MXN",
                "university": "UTTT",
                "essentialServices": ["internet"],
                "petsAllowed": None,
                "maxDistanceKm": None,
            }
        },
        ensure_ascii=False,
    )


def _last_parse_record(caplog: pytest.LogCaptureFixture) -> logging.LogRecord:
    """Select the use-case record, ignoring unrelated loggers."""

    records = [
        record
        for record in caplog.records
        if record.name == "thehouse_genai.application.parse_search"
    ]
    assert records
    return records[-1]


@pytest.mark.parametrize(
    ("term", "reason"),
    [
        (_BLOCK_TERM, "INPUT_MODERATION_BLOCKED"),
        (_REVIEW_TERM, "INPUT_MODERATION_REVIEW"),
    ],
)
def test_lexicon_term_in_query_fails_closed_before_the_provider(
    term: str,
    reason: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A fictitious block/review term is rejected by the real local policy."""

    caplog.set_level(logging.DEBUG)
    _patch_lexicon(monkeypatch)
    provider = FakeProvider(text=_completion())

    response = asyncio.run(
        ParseSearch(provider).execute(
            _request(f"Busco cuarto con {term} cerca de la UTTT con internet")
        )
    )

    assert response.filters == empty_filters()
    assert response.confidence is SearchConfidence.LOW
    assert response.generated is False
    assert provider.calls == []
    assert _last_parse_record(caplog).fallback_reason == reason


@pytest.mark.parametrize(
    "leak",
    [
        "estudiante@ejemplo.mx",
        "+52 55 1234 5678",
        "55 1234 5678",
        "www.ejemplo.mx/cuarto",
        _BLOCK_TERM,
    ],
)
def test_pii_or_blocked_term_in_completion_fails_closed(
    leak: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The real local moderator rejects a completion carrying PII or a blocked term."""

    caplog.set_level(logging.DEBUG)
    _patch_lexicon(monkeypatch)
    completion = json.dumps(
        {"filters": {"university": f"UTTT {leak}"}}, ensure_ascii=False
    )

    response = asyncio.run(
        ParseSearch(
            FakeProvider(text=completion), moderator=LocalRuleModerator()
        ).execute(_request("Busco cuarto cerca de la UTTT"))
    )

    assert response.filters == empty_filters()
    assert response.confidence is SearchConfidence.LOW
    assert response.generated is False
    assert _last_parse_record(caplog).fallback_reason == "MODERATION_BLOCKED"


def test_unexpected_moderator_error_fails_closed_without_leaking_detail(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Even an unexpected moderator exception yields the empty fallback.

    B3 covers the normalized moderation error; this exercises the generic exception
    branch and checks that no detail from the failure reaches the client or the logs.
    """

    caplog.set_level(logging.DEBUG)
    detail = "moderator-detail-marker"
    moderator = FakeModerationProvider(error=RuntimeError(detail))

    response = asyncio.run(
        ParseSearch(FakeProvider(text=_completion()), moderator=moderator).execute(
            _request("Busco cuarto cerca de la UTTT")
        )
    )

    assert response.filters == empty_filters()
    assert response.confidence is SearchConfidence.LOW
    assert response.generated is False
    assert _last_parse_record(caplog).fallback_reason == "MODERATION_UNAVAILABLE"
    logged = "\n".join(
        str(value) for record in caplog.records for value in record.__dict__.values()
    )
    assert detail not in logged
    assert detail not in str(response.model_dump(by_alias=True))
