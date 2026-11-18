"""Domain contracts and deterministic extractors for natural-language search filters.

GenAI extracts only what the student actually wrote. Backend remains the source of truth
for universities and services, so this module owns no catalog of properties: it only
normalizes evidence found in the query. Every filter emitted by the model is checked
against that evidence before it reaches the response (spec 004).

HTTP names are camelCase aliases; Python code uses snake_case. All models are frozen and
closed to unknown fields so a property or a result of a search can never enter the prompt
or the response.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from thehouse_genai.domain.moderation import normalize_text
from thehouse_genai.domain.text_guard import escape_untrusted, is_control

_DEFAULT_CURRENCY: Final[str] = "MXN"
_MAX_QUERY_CHARS: Final[int] = 500
_MAX_UNIVERSITY_CHARS: Final[int] = 120
_MAX_SERVICES: Final[int] = 8
_MAX_BUDGET: Final[Decimal] = Decimal("1_000_000")
_MAX_DISTANCE_KM: Final[Decimal] = Decimal("100")

# The service vocabulary of decision D12 of 003, without `mascotas`: pets are reported
# by the separate boolean filter and must never be double counted.
SERVICE_VOCABULARY: Final[frozenset[str]] = frozenset(
    {
        "internet",
        "agua",
        "luz",
        "gas",
        "estacionamiento",
        "lavadora",
        "amueblado",
        "baño privado",
    }
)

# Aliases are input normalizers, not a catalog: only a mention in the query can produce
# a value, and Backend still validates it against its own catalog.
UNIVERSITY_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "UTTT": ("uttt", "universidad tecnologica de tula-tepeji", "ut tula tepeji"),
}

_MODEL_CONFIG: Final[ConfigDict] = ConfigDict(
    extra="forbid",
    frozen=True,
    populate_by_name=True,
)

_NUMBER: Final[str] = r"\d[\d,]*(?:\.\d+)?"
_CURRENCY_SYMBOL_PATTERN: Final[re.Pattern[str]] = re.compile(r"\$\s*(" + _NUMBER + r")")
_MIL_K_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(?:mil|k)\b", re.IGNORECASE
)
_MONEY_WORD_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(" + _NUMBER + r")\s*(?:pesos?|mxn)\b", re.IGNORECASE
)
_MONEY_CUE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:presupuesto|hasta|m[áa]ximo|menos de|no m[áa]s de|por debajo de)"
    r"\s*(?:de\s*)?(" + _NUMBER + r")"
    r"(?!\s*(?:mil|k|pesos?|mxn)\b)",
    re.IGNORECASE,
)
_RANGE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\bentre\s+(" + _NUMBER + r")\s*(?:y|e)\s*(" + _NUMBER + r")\b", re.IGNORECASE
)
_OTHER_CURRENCY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:usd|d[óo]lares?|dolar|eur|euros?|gbp|libras?)\b", re.IGNORECASE
)
_DISTANCE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(?:kms?|kil[óo]metros?)\b", re.IGNORECASE
)
_ACRONYM_PATTERN: Final[re.Pattern[str]] = re.compile(r"\b[A-Z]{2,6}\b")
_ACRONYM_EXCLUSIONS: Final[frozenset[str]] = frozenset(
    {"MXN", "USD", "EUR", "GBP", "URL", "KMS", "IVA"}
)

_SERVICE_SYNONYMS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (re.compile(r"\b(?:internet|wifi|wi-fi|wi fi|red)\b"), "internet"),
    (re.compile(r"\bagua\b"), "agua"),
    (re.compile(r"\bluz\b"), "luz"),
    (re.compile(r"\bgas\b"), "gas"),
    (re.compile(r"\b(?:estacionamiento|cochera|parqueo)\b"), "estacionamiento"),
    (re.compile(r"\blavadora\b"), "lavadora"),
    (re.compile(r"\bamueblad[oa]s?\b"), "amueblado"),
    (re.compile(r"\bbano\s+(?:privado|propio)\b"), "baño privado"),
)
_POSITIVE_PET_PATTERN: Final[re.Pattern[str]] = re.compile(r"\bmascotas?\b|\bperros?\b|\bgatos?\b")
_NEGATIVE_PET_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\bsin\s+(?:mascotas?|perros?|gatos?)\b"
    r"|\bno\s+(?:acepto|se aceptan|quiero|tengo|hay)?\s*(?:mascotas?|perros?|gatos?)\b"
)


def _to_decimal(raw: str, *, comma_is_decimal: bool) -> Decimal | None:
    """Parse a numeric token, rejecting overprecision and out-of-range values."""

    cleaned = raw.replace(",", ".") if comma_is_decimal else raw.replace(",", "")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    exponent = value.as_tuple().exponent
    if not value.is_finite() or value < 0 or (isinstance(exponent, int) and exponent < -2):
        return None
    return value


@dataclass(frozen=True)
class MoneyEvidence:
    """Money amounts found in the query and the rule that produced them."""

    amounts: tuple[Decimal, ...]
    is_range: bool = False
    has_other_currency: bool = False


def extract_money_evidence(text: str) -> MoneyEvidence:
    """Collect money amounts, ignoring distances, years and phone numbers.

    "3 mil" and "3k" mean 3000; "3 km" is a distance. A range such as "entre 2000 y
    3000" is flagged so the upper bound is used and confidence stays at most medium.
    """

    distance_spans = [(match.start(), match.end()) for match in _DISTANCE_PATTERN.finditer(text)]
    raw_amounts: list[Decimal] = []

    def _accept(value: Decimal | None) -> None:
        if value is not None and value <= _MAX_BUDGET:
            raw_amounts.append(value)

    for match in _CURRENCY_SYMBOL_PATTERN.finditer(text):
        _accept(_to_decimal(match.group(1), comma_is_decimal=False))
    for match in _MIL_K_PATTERN.finditer(text):
        base = _to_decimal(match.group(1), comma_is_decimal=True)
        if base is not None:
            _accept(base * Decimal("1000"))
    for match in _MONEY_WORD_PATTERN.finditer(text):
        _accept(_to_decimal(match.group(1), comma_is_decimal=False))
    for match in _MONEY_CUE_PATTERN.finditer(text):
        if any(match.start() < end and start < match.end() for start, end in distance_spans):
            continue
        _accept(_to_decimal(match.group(1), comma_is_decimal=False))

    is_range = False
    range_match = _RANGE_PATTERN.search(text)
    if range_match is not None:
        lower = _to_decimal(range_match.group(1), comma_is_decimal=False)
        upper = _to_decimal(range_match.group(2), comma_is_decimal=False)
        if lower is not None and upper is not None:
            is_range = True
            raw_amounts = [lower, upper]

    return MoneyEvidence(
        amounts=tuple(sorted(set(raw_amounts))),
        is_range=is_range,
        has_other_currency=bool(_OTHER_CURRENCY_PATTERN.search(text)),
    )


def chosen_budget(evidence: MoneyEvidence) -> Decimal | None:
    """Return the budget backed by the text, or None when it is ambiguous or foreign."""

    if evidence.has_other_currency or not evidence.amounts:
        return None
    if evidence.is_range:
        return max(evidence.amounts)
    if len(evidence.amounts) == 1:
        return evidence.amounts[0]
    return None


def extract_distance_km(text: str) -> Decimal | None:
    """Return the largest distance explicitly written in kilometers, if any."""

    values: list[Decimal] = []
    for match in _DISTANCE_PATTERN.finditer(text):
        value = _to_decimal(match.group(1), comma_is_decimal=True)
        if value is not None and value <= _MAX_DISTANCE_KM:
            values.append(value)
    return max(values) if values else None


def _whole_word(alias: str, folded_text: str) -> bool:
    """Report whether a folded alias occurs as a whole word in folded text."""

    return re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", folded_text) is not None


def extract_university(text: str) -> str | None:
    """Return a canonical alias or an explicit acronym backed by the query."""

    folded = normalize_text(text)
    for canonical, aliases in UNIVERSITY_ALIASES.items():
        if any(_whole_word(alias, folded) for alias in aliases):
            return canonical
    for match in _ACRONYM_PATTERN.finditer(text):
        token = match.group(0)
        if token not in _ACRONYM_EXCLUSIONS:
            return token
    return None


def is_university_grounded(value: str, text: str) -> bool:
    """Report whether a returned university is backed by the query."""

    folded = normalize_text(text)
    if _whole_word(normalize_text(value), folded):
        return True
    aliases = UNIVERSITY_ALIASES.get(value, ())
    return any(_whole_word(alias, folded) for alias in aliases)


def extract_services(text: str) -> tuple[str, ...]:
    """Return the distinct known services explicitly mentioned in the query."""

    folded = normalize_text(text)
    found = {
        canonical
        for pattern, canonical in _SERVICE_SYNONYMS
        if pattern.search(folded) is not None
    }
    return tuple(sorted(found))


def extract_pets(text: str) -> bool | None:
    """Return True for a positive mention; negative or absent mentions stay None."""

    folded = normalize_text(text)
    if _NEGATIVE_PET_PATTERN.search(folded) is not None:
        return None
    if _POSITIVE_PET_PATTERN.search(folded) is not None:
        return True
    return None


class SearchConfidence(StrEnum):
    """Bounded confidence vocabulary, computed by the service, never by the model."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SearchFilters(BaseModel):
    """The only filters GenAI may return; null or empty means not mentioned."""

    model_config = _MODEL_CONFIG

    max_budget: Decimal | None = Field(
        default=None, alias="maxBudget", ge=0, le=_MAX_BUDGET, max_digits=12, decimal_places=2
    )
    currency: Literal["MXN"] | None = None
    university: str | None = Field(default=None, min_length=1, max_length=_MAX_UNIVERSITY_CHARS)
    essential_services: list[str] = Field(
        default_factory=list, alias="essentialServices", max_length=_MAX_SERVICES
    )
    pets_allowed: bool | None = Field(default=None, alias="petsAllowed")
    max_distance_km: Decimal | None = Field(
        default=None, alias="maxDistanceKm", ge=0, le=_MAX_DISTANCE_KM, max_digits=5,
        decimal_places=2,
    )

    @field_validator("essential_services")
    @classmethod
    def _check_services(cls, value: list[str]) -> list[str]:
        for service in value:
            if service not in SERVICE_VOCABULARY:
                raise ValueError("unknown service")
        if len(set(value)) != len(value):
            raise ValueError("duplicate service")
        return sorted(value)


def empty_filters() -> SearchFilters:
    """Build the safe fallback: no filter is asserted about the student."""

    return SearchFilters()


def has_any_filter(filters: SearchFilters) -> bool:
    """Report whether at least one filter carries a value."""

    return any(
        (
            filters.max_budget is not None,
            filters.currency is not None,
            filters.university is not None,
            bool(filters.essential_services),
            filters.pets_allowed is not None,
            filters.max_distance_km is not None,
        )
    )


class ParseSearchRequest(BaseModel):
    """Closed input of the parse-search endpoint."""

    model_config = _MODEL_CONFIG

    query: str = Field(min_length=1, max_length=_MAX_QUERY_CHARS)
    locale: Literal["es-MX"] = "es-MX"

    @field_validator("query")
    @classmethod
    def _query_is_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        if any(is_control(char) for char in value):
            raise ValueError("query must not contain control characters")
        return value

    def to_context(self, query: str | None = None) -> str:
        """Serialize only allowlisted facts, escaping untrusted free text."""

        safe_query = escape_untrusted(query if query is not None else self.query)
        return f"query: {safe_query}\nlocale: {self.locale}"


class ParseSearchCompletion(BaseModel):
    """The only completion shape accepted from the model: filters and nothing else."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    filters: SearchFilters


class ParseSearchResponse(BaseModel):
    """The only payload returned to Backend; no provider detail is included."""

    model_config = _MODEL_CONFIG

    filters: SearchFilters
    confidence: SearchConfidence
    generated: bool
    prompt_version: str = Field(alias="promptVersion")
