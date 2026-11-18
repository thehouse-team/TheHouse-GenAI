"""Versioned Spanish query corpus for parse-search.

Every completion comes from FakeProvider with the exact expected filters, so these tests
exercise the real guardrails and confidence rules without any network call. The corpus
contains only synthetic PII and invented moderation tokens.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from thehouse_genai.application.parse_search import PARSE_SEARCH_PROMPT_VERSION, ParseSearch
from thehouse_genai.domain.search_filters import ParseSearchRequest
from thehouse_genai.providers.fake import FakeProvider

_CORPUS_PATH = Path(__file__).parent / "fixtures" / "search_query_corpus.json"
_CATEGORIES = frozenset({"positive", "ambiguous", "adversarial", "pii", "moderation"})
_CONFIDENCES = frozenset({"low", "medium", "high"})
_FILTER_KEYS = {
    "maxBudget",
    "currency",
    "maxDistanceKm",
    "university",
    "essentialServices",
    "petsAllowed",
}
_CASE_KEYS = {"id", "query", "expectedFilters", "expectedConfidence", "category"}


def _corpus() -> dict[str, Any]:
    return json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


def test_corpus_is_versioned_and_complete() -> None:
    payload = _corpus()
    cases = payload["cases"]

    assert payload["version"] == "1.0"
    assert 28 <= len(cases) <= 30
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["category"] for case in cases} == _CATEGORIES
    for case in cases:
        assert set(case) == _CASE_KEYS, case["id"]
        assert isinstance(case["query"], str) and 1 <= len(case["query"]) <= 500
        assert case["category"] in _CATEGORIES
        assert case["expectedConfidence"] in _CONFIDENCES
        assert set(case["expectedFilters"]) == _FILTER_KEYS, case["id"]


@pytest.mark.parametrize("case", _corpus()["cases"], ids=lambda item: item["id"])
def test_expected_filters_survive_the_guardrails(case: dict[str, Any]) -> None:
    completion = json.dumps({"filters": case["expectedFilters"]}, ensure_ascii=False)
    request = ParseSearchRequest.model_validate({"query": case["query"]})

    response = asyncio.run(ParseSearch(FakeProvider(text=completion)).execute(request))
    body = response.model_dump(mode="json", by_alias=True)

    assert body["filters"] == case["expectedFilters"], case["id"]
    assert body["confidence"] == case["expectedConfidence"], case["id"]
    assert body["generated"] is bool(case["expectedFilters"] != _empty_filters()), case["id"]
    assert body["promptVersion"] == PARSE_SEARCH_PROMPT_VERSION


def _empty_filters() -> dict[str, object]:
    """Return the canonical empty filter set for the generated-flag assertion."""

    return {
        "maxBudget": None,
        "currency": None,
        "maxDistanceKm": None,
        "university": None,
        "essentialServices": [],
        "petsAllowed": None,
    }
