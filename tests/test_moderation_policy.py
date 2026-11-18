"""Tests for the versioned local moderation policy and its detectors.

No real offensive term is written here: lexicon tests inject fictitious tokens through
a monkeypatched lexicon. The suite never reaches the network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from thehouse_genai.domain import moderation
from thehouse_genai.domain.moderation import (
    DECISION_PRIORITY,
    POLICY_VERSION,
    Lexicon,
    ModerationCategory,
    ModerationDecision,
    ModerationReason,
    classify,
    detect_email,
    detect_offensive,
    detect_phone,
    detect_url,
    load_lexicon,
    normalize_text,
)

_CORPUS_PATH = Path(__file__).parent / "fixtures" / "moderation_benign_corpus.json"
_REQUIRED_PHRASES = (
    "$2,800 MXN",
    "1.3 km",
    "91%",
    "depósito de garantía",
    "se aceptan mascotas",
    "baño privado",
    "cerca de la UTTT",
)


def _fictitious_lexicon(
    *,
    block: tuple[str, ...] = ("zorbaflux",),
    review: tuple[str, ...] = ("plimbo",),
    allowlist: tuple[str, ...] = (),
) -> Lexicon:
    """Build a lexicon made only of invented tokens."""

    return Lexicon(
        version="test",
        block=frozenset(block),
        review=frozenset(review),
        allowlist=frozenset(allowlist),
    )


def _patch_lexicon(monkeypatch: pytest.MonkeyPatch, lexicon: Lexicon) -> None:
    """Replace the on-disk lexicon with an in-memory one for one test."""

    monkeypatch.setattr(moderation, "load_lexicon", lambda: lexicon)


def _corpus() -> dict[str, Any]:
    """Read the versioned benign corpus."""

    return json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


def test_policy_version_and_priority() -> None:
    assert POLICY_VERSION == "moderation_v1"
    assert DECISION_PRIORITY == (
        ModerationDecision.ALLOW,
        ModerationDecision.REVIEW,
        ModerationDecision.BLOCK,
    )


def test_normalize_text_folds_accents_and_case() -> None:
    assert normalize_text("ZÓRBAFLUX") == "zorbaflux"
    assert normalize_text("se aceptan mascotas") == "se aceptan mascotas"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("contacta a estudiante@ejemplo.mx", True),
        ("correo: nombre.apellido@universidad.edu.mx", True),
        ("sin correo aqui", False),
        ("cuesta 2800 MXN", False),
    ],
)
def test_email_detector(text: str, expected: bool) -> None:
    assert detect_email(text) is expected


@pytest.mark.parametrize(
    "text",
    [
        "5512345678",
        "55 1234 5678",
        "55-1234-5678",
        "55.1234.5678",
        "(55) 1234-5678",
        "+52 55 1234 5678",
        "+525512345678",
    ],
)
def test_phone_detector_accepts_ten_digits_with_optional_country_code(text: str) -> None:
    assert detect_phone(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "$2,800 MXN",
        "$3,000 MXN",
        "1.3 km",
        "91%",
        "2026-11-18",
        "2800",
        "123456789",
        "12 3456 7890 1",
    ],
)
def test_phone_detector_ignores_prices_distances_and_dates(text: str) -> None:
    assert detect_phone(text) is False


@pytest.mark.parametrize(
    "text",
    [
        "https://ejemplo.mx/cuarto",
        "http://ejemplo.mx",
        "www.ejemplo.mx",
        "Visita www.ejemplo.mx para mas detalles.",
    ],
)
def test_url_detector_requires_a_scheme_or_www(text: str) -> None:
    assert detect_url(text) is True


@pytest.mark.parametrize(
    "text",
    ["uttt.edu.mx", "cerca de la UTTT", "Cuesta $2,800 MXN", "sin enlaces"],
)
def test_url_detector_ignores_bare_domains(text: str) -> None:
    assert detect_url(text) is False


def test_shipped_lexicon_has_empty_lists() -> None:
    lexicon = load_lexicon()

    assert lexicon.version == "1.0"
    assert lexicon.block == frozenset()
    assert lexicon.review == frozenset()
    assert lexicon.allowlist == frozenset()


@pytest.mark.parametrize("text", ["El zorbaflux aparece aqui.", "ZORBAFLUX", "zórbaflux"])
def test_fictitious_block_term_blocks(
    text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_lexicon(monkeypatch, _fictitious_lexicon())

    assert detect_offensive(text) is ModerationDecision.BLOCK
    verdict = classify(text)
    assert verdict.decision is ModerationDecision.BLOCK
    assert verdict.reasons == (ModerationReason.OFFENSIVE,)


def test_fictitious_review_term_reviews(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_lexicon(monkeypatch, _fictitious_lexicon())

    verdict = classify("Hay un plimbo en el texto.")

    assert verdict.decision is ModerationDecision.REVIEW
    assert verdict.reasons == (ModerationReason.OFFENSIVE,)


@pytest.mark.parametrize("text", ["zorbafluxito", "prezorbaflux", "sintermino"])
def test_offensive_terms_match_only_whole_words(
    text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_lexicon(monkeypatch, _fictitious_lexicon())

    assert detect_offensive(text) is None
    assert classify(text).decision is ModerationDecision.ALLOW


def test_allowlist_suppresses_a_lexicon_match(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_lexicon(
        monkeypatch,
        _fictitious_lexicon(review=("plimbo",), allowlist=("plimbo",)),
    )

    assert detect_offensive("El plimbo es parte del barrio.") is None
    assert classify("El plimbo es parte del barrio.").decision is ModerationDecision.ALLOW


def test_block_wins_over_review(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_lexicon(monkeypatch, _fictitious_lexicon())

    verdict = classify("Estudiante@ejemplo.mx menciona plimbo y zorbaflux.")

    assert verdict.decision is ModerationDecision.BLOCK
    assert ModerationReason.EMAIL in verdict.reasons
    assert ModerationReason.OFFENSIVE in verdict.reasons
    assert verdict.categories == (
        ModerationCategory.OFFENSIVE,
        ModerationCategory.PII,
    )


def test_classify_emits_stable_codes_and_policy_version() -> None:
    verdict = classify("Escribe a nombre@ejemplo.mx")

    assert verdict.reasons == (ModerationReason.EMAIL,)
    assert verdict.categories == (ModerationCategory.PII,)
    assert verdict.policy_version == POLICY_VERSION


def test_empty_text_is_allowed() -> None:
    verdict = classify("")

    assert verdict.decision is ModerationDecision.ALLOW
    assert verdict.reasons == ()
    assert verdict.categories == ()


def test_benign_corpus_is_versioned_and_complete() -> None:
    corpus = _corpus()

    assert corpus["version"] == "1.0"
    assert len(corpus["cases"]) >= len(_REQUIRED_PHRASES)
    assert len({case["id"] for case in corpus["cases"]}) == len(corpus["cases"])
    joined = " ".join(case["text"] for case in corpus["cases"]).lower()
    for phrase in _REQUIRED_PHRASES:
        assert phrase.lower() in joined, phrase


@pytest.mark.parametrize("case", _corpus()["cases"], ids=lambda c: c["id"])
def test_benign_corpus_is_never_flagged(case: dict[str, Any]) -> None:
    verdict = classify(case["text"])

    assert verdict.decision is ModerationDecision.ALLOW, case["text"]
    assert verdict.reasons == ()
    assert verdict.categories == ()


@pytest.mark.parametrize("case", _corpus()["cases"], ids=lambda c: c["id"])
def test_benign_corpus_is_not_flagged_by_a_custom_lexicon(
    case: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_lexicon(monkeypatch, _fictitious_lexicon())

    assert classify(case["text"]).decision is ModerationDecision.ALLOW
