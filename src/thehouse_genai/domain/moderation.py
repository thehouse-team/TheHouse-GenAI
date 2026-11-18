"""Versioned moderation policy and deterministic local detectors.

The offensive lexicon is data, not code: it lives in ``moderation_lexicon.json`` next to
this module and is loaded at runtime. The shipped file has empty lists; the operator
fills it. This module owns the policy, the reason codes, the decision priority and the
pure detectors. It has no dependency on providers, the API, the network or an LLM.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

POLICY_VERSION: Final[str] = "moderation_v1"
MAX_TEXT_CHARS: Final[int] = 900

_LEXICON_PATH: Final[Path] = Path(__file__).with_name("moderation_lexicon.json")


class ModerationDecision(StrEnum):
    """The three outcomes of a moderation decision."""

    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"


# Lowest to highest: the last matching rule wins.
DECISION_PRIORITY: Final[tuple[ModerationDecision, ...]] = (
    ModerationDecision.ALLOW,
    ModerationDecision.REVIEW,
    ModerationDecision.BLOCK,
)


class ModerationCategory(StrEnum):
    """Bounded categories recorded in logs; never the matched text."""

    PII = "PII"
    URL = "URL"
    OFFENSIVE = "OFFENSIVE"


class ModerationReason(StrEnum):
    """Stable, log-safe reason codes."""

    EMAIL = "PII_EMAIL"
    PHONE = "PII_PHONE"
    URL = "URL_EXTERNAL"
    OFFENSIVE = "OFFENSIVE_LANGUAGE"


@dataclass(frozen=True)
class ModerationVerdict:
    """Pure result of classifying one piece of text."""

    decision: ModerationDecision
    reasons: tuple[ModerationReason, ...]
    categories: tuple[ModerationCategory, ...]
    policy_version: str = POLICY_VERSION


@dataclass(frozen=True)
class Lexicon:
    """Normalized terms loaded from the versioned data file."""

    version: str
    block: frozenset[str]
    review: frozenset[str]
    allowlist: frozenset[str]


class _LexiconFile(BaseModel):
    """Shape of the on-disk file; unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    block: list[str] = Field(default_factory=list)
    review: list[str] = Field(default_factory=list)
    allowlist: list[str] = Field(default_factory=list)


_EMAIL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}\b"
)
# Ten digits: optional +52 prefix, a two-digit area code and an eight-digit number.
# Separators are spaces, dots or hyphens; commas are never accepted, so a price such as
# $2,800 cannot be read as a phone number.
_PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![0-9])"
    r"(?:\+52[\s.\-]?)?"
    r"(?:\(?[0-9]{2}\)?[\s.\-]?)"
    r"[0-9]{4}[\s.\-]?[0-9]{4}"
    r"(?![\s.\-]?[0-9])"
)
_URL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE
)
_URL_TRAILING: Final[str] = ".,;:!?)\\]}>\"'"


def normalize_text(text: str) -> str:
    """Fold accents and case for detection, without changing the caller's text."""

    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return without_marks.casefold()


@lru_cache(maxsize=1)
def load_lexicon() -> Lexicon:
    """Read and validate the shipped lexicon; the file never contains real terms here."""

    payload = _LexiconFile.model_validate_json(_LEXICON_PATH.read_text(encoding="utf-8"))
    return Lexicon(
        version=payload.version,
        block=frozenset(normalize_text(term) for term in payload.block if term.strip()),
        review=frozenset(normalize_text(term) for term in payload.review if term.strip()),
        allowlist=frozenset(
            normalize_text(term) for term in payload.allowlist if term.strip()
        ),
    )


def _compile_terms(terms: frozenset[str]) -> re.Pattern[str] | None:
    """Build a whole-word pattern from normalized terms, including multiword terms."""

    alternatives: list[str] = []
    for term in sorted(terms):
        tokens = [token for token in term.split() if token]
        if not tokens:
            continue
        alternatives.append(r"\s+".join(re.escape(token) for token in tokens))
    if not alternatives:
        return None
    return re.compile(r"\b(?:" + "|".join(alternatives) + r")\b")


def _mask_allowlist(text: str, allowlist: frozenset[str]) -> str:
    """Blank out allowlisted phrases before looking for offensive terms."""

    masked = text
    for term in sorted(allowlist):
        pattern = _compile_terms(frozenset({term}))
        if pattern is not None:
            masked = pattern.sub(" ", masked)
    return masked


def detect_email(text: str) -> bool:
    """Report whether the text contains an email address."""

    return _EMAIL_PATTERN.search(normalize_text(text)) is not None


def detect_phone(text: str) -> bool:
    """Report whether the text contains a ten-digit phone number, with optional +52."""

    return _PHONE_PATTERN.search(normalize_text(text)) is not None


def detect_url(text: str) -> bool:
    """Report whether the text contains a URL with a scheme or a ``www.`` prefix."""

    folded = normalize_text(text)
    return any(
        match.group().rstrip(_URL_TRAILING) for match in _URL_PATTERN.finditer(folded)
    )


def detect_offensive(
    text: str,
    lexicon: Lexicon | None = None,
) -> ModerationDecision | None:
    """Return the severity of a lexicon match, or None when the text is clean."""

    active = lexicon if lexicon is not None else load_lexicon()
    masked = _mask_allowlist(normalize_text(text), active.allowlist)
    block_pattern = _compile_terms(active.block)
    if block_pattern is not None and block_pattern.search(masked):
        return ModerationDecision.BLOCK
    review_pattern = _compile_terms(active.review)
    if review_pattern is not None and review_pattern.search(masked):
        return ModerationDecision.REVIEW
    return None


def _higher(current: ModerationDecision, candidate: ModerationDecision) -> ModerationDecision:
    """Apply the agreed priority: block > review > allow."""

    if DECISION_PRIORITY.index(candidate) > DECISION_PRIORITY.index(current):
        return candidate
    return current


def classify(text: str, *, lexicon: Lexicon | None = None) -> ModerationVerdict:
    """Classify one piece of text using only local, deterministic rules."""

    folded = normalize_text(text)
    reasons: set[ModerationReason] = set()
    categories: set[ModerationCategory] = set()
    decision = ModerationDecision.ALLOW

    if _EMAIL_PATTERN.search(folded):
        reasons.add(ModerationReason.EMAIL)
        categories.add(ModerationCategory.PII)
        decision = _higher(decision, ModerationDecision.BLOCK)

    if _PHONE_PATTERN.search(folded):
        reasons.add(ModerationReason.PHONE)
        categories.add(ModerationCategory.PII)
        decision = _higher(decision, ModerationDecision.BLOCK)

    if detect_url(folded):
        reasons.add(ModerationReason.URL)
        categories.add(ModerationCategory.URL)
        decision = _higher(decision, ModerationDecision.BLOCK)

    offensive = detect_offensive(folded, lexicon)
    if offensive is not None:
        reasons.add(ModerationReason.OFFENSIVE)
        categories.add(ModerationCategory.OFFENSIVE)
        decision = _higher(decision, offensive)

    return ModerationVerdict(
        decision=decision,
        reasons=tuple(sorted(reasons, key=lambda reason: reason.value)),
        categories=tuple(sorted(categories, key=lambda category: category.value)),
    )


@dataclass(frozen=True)
class RedactionResult:
    """The text after PII removal, with only stable reason codes."""

    text: str
    reasons: tuple[ModerationReason, ...]


# The redaction patterns are derived from the exact detector patterns above, so the
# policy and the removal cannot drift apart. `re.IGNORECASE` is added because the
# detectors fold case before matching while redaction works on the original text.
_EMAIL_REDACT_PATTERN: Final[re.Pattern[str]] = re.compile(
    _EMAIL_PATTERN.pattern, re.IGNORECASE
)
_PHONE_REDACT_PATTERN: Final[re.Pattern[str]] = re.compile(
    _PHONE_PATTERN.pattern, re.IGNORECASE
)


def redact_pii(text: str) -> RedactionResult:
    """Replace emails, phone numbers and URLs before untrusted text reaches a prompt.

    Replacements are applied from the end of the string so earlier spans stay valid.
    Overlapping matches are resolved in favor of the first one: a URL is replaced
    before any email it may contain. Prices, distances and years are never matched.
    """

    spans: list[tuple[int, int, str, ModerationReason]] = []
    for match in _URL_PATTERN.finditer(text):
        core = match.group().rstrip(_URL_TRAILING)
        if core:
            spans.append((match.start(), match.start() + len(core), "[URL]", ModerationReason.URL))
    for match in _EMAIL_REDACT_PATTERN.finditer(text):
        spans.append((match.start(), match.end(), "[EMAIL]", ModerationReason.EMAIL))
    for match in _PHONE_REDACT_PATTERN.finditer(text):
        spans.append((match.start(), match.end(), "[TELEFONO]", ModerationReason.PHONE))

    accepted: list[tuple[int, int, str, ModerationReason]] = []
    last_end = -1
    for start, end, replacement, reason in sorted(spans, key=lambda item: (item[0], item[1])):
        if start < last_end:
            continue
        accepted.append((start, end, replacement, reason))
        last_end = end

    redacted = text
    reasons: set[ModerationReason] = set()
    for start, end, replacement, reason in reversed(accepted):
        redacted = redacted[:start] + replacement + redacted[end:]
        reasons.add(reason)
    return RedactionResult(
        text=redacted,
        reasons=tuple(sorted(reasons, key=lambda reason: reason.value)),
    )
