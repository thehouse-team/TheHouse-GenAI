"""Domain contracts and pure guardrails for match explanations.

The HTTP shape uses camelCase aliases because Backend already reviews that contract;
Python code works with snake_case attributes. Every model is frozen and closes to
unknown fields, so no extra data can reach the prompt or the response.

This module owns the invariants of the explanation use case: input limits, the
allowlist of numbers and services, and the safe serialization of untrusted text. It
has no dependency on providers, the API or infrastructure.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from thehouse_genai.domain.text_guard import (
    escape_untrusted as _escape_text,
)
from thehouse_genai.domain.text_guard import (
    is_control as _is_control,
)

_DEFAULT_CURRENCY: Final[str] = "MXN"
_LOCALE: Final[str] = "es-MX"
_MAX_SERVICE_CHARS: Final[int] = 40
_MAX_TEXT_CHARS: Final[int] = 120
_MAX_EXPLANATION_CHARS: Final[int] = 900

# Initial service vocabulary (decision D12). It is used by the output validator to
# detect invented services; it is not a whitelist for the input, which only rejects
# control characters and overlong names.
KNOWN_SERVICES: Final[frozenset[str]] = frozenset(
    {
        "internet",
        "agua",
        "luz",
        "gas",
        "estacionamiento",
        "lavadora",
        "amueblado",
        "baño privado",
        "mascotas",
    }
)

# Fields that may reach the LLM prompt (spec 005, RF-03). Any new request field must be
# added here explicitly: tests pin this list to the model schema and to the keys emitted
# by `to_context()`, so the two cannot drift apart unnoticed.
PROMPT_FIELD_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "matchScore",
        "locale",
        "university",
        "property.title",
        "property.price",
        "property.currency",
        "property.distanceKm",
        "property.services",
        "preferences.budgetMax",
        "preferences.currency",
        "preferences.maxDistanceKm",
        "preferences.essentialServices",
    }
)

_NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
_MODEL_CONFIG: Final[ConfigDict] = ConfigDict(
    extra="forbid",
    frozen=True,
    populate_by_name=True,
)


def _validate_services(value: list[str]) -> list[str]:
    """Accept any service label except control characters and overlong names."""

    for service in value:
        if len(service) > _MAX_SERVICE_CHARS:
            raise ValueError(f"service names must be at most {_MAX_SERVICE_CHARS} characters")
        if any(_is_control(char) for char in service):
            raise ValueError("service names must not contain control characters")
    return value


def _decimal_text(value: float) -> str:
    """Render a float as a clean decimal string without binary artifacts."""

    return str(Decimal(str(value)))


def _to_decimal(value: Decimal | float | int) -> Decimal:
    """Convert an input number to Decimal without float rounding noise."""

    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class PropertyIn(BaseModel):
    """The property facts received from Backend."""

    model_config = _MODEL_CONFIG

    title: str = Field(min_length=1, max_length=_MAX_TEXT_CHARS)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    distance_km: float = Field(ge=0, le=1_000, alias="distanceKm")
    services: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("services")
    @classmethod
    def _check_services(cls, value: list[str]) -> list[str]:
        return _validate_services(value)


class PreferencesIn(BaseModel):
    """The student preferences received from Backend."""

    model_config = _MODEL_CONFIG

    budget_max: Decimal = Field(ge=0, max_digits=12, decimal_places=2, alias="budgetMax")
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    max_distance_km: float = Field(ge=0, le=1_000, alias="maxDistanceKm")
    essential_services: list[str] = Field(
        default_factory=list, max_length=20, alias="essentialServices"
    )

    @field_validator("essential_services")
    @classmethod
    def _check_services(cls, value: list[str]) -> list[str]:
        return _validate_services(value)


class ExplainMatchRequest(BaseModel):
    """Complete, closed input of the explain-match endpoint."""

    model_config = _MODEL_CONFIG

    match_score: int = Field(ge=0, le=100, alias="matchScore")
    locale: Literal["es-MX"] = "es-MX"
    university: str = Field(min_length=1, max_length=_MAX_TEXT_CHARS)
    property: PropertyIn
    preferences: PreferencesIn

    @model_validator(mode="after")
    def _currencies_match(self) -> Self:
        """Reject inconsistent currency data instead of inventing a conversion."""

        if self.property.currency != self.preferences.currency:
            raise ValueError("property.currency and preferences.currency must match")
        return self

    def to_context(self) -> str:
        """Serialize only allowlisted facts as `key: value` lines.

        Every free-text value is escaped before it enters the prompt, so untrusted
        content cannot inject instructions or close the delimited data block.
        """

        services = ", ".join(_escape_text(service) for service in self.property.services)
        essential = ", ".join(
            _escape_text(service) for service in self.preferences.essential_services
        )
        lines = (
            f"matchScore: {self.match_score}",
            f"locale: {self.locale}",
            f"university: {_escape_text(self.university)}",
            f"property.title: {_escape_text(self.property.title)}",
            f"property.price: {self.property.price}",
            f"property.currency: {self.property.currency}",
            f"property.distanceKm: {_decimal_text(self.property.distance_km)}",
            f"property.services: {services}",
            f"preferences.budgetMax: {self.preferences.budget_max}",
            f"preferences.currency: {self.preferences.currency}",
            f"preferences.maxDistanceKm: {_decimal_text(self.preferences.max_distance_km)}",
            f"preferences.essentialServices: {essential}",
        )
        return "\n".join(lines)


class ExplainMatchResponse(BaseModel):
    """The only payload returned to Backend; no provider detail is included."""

    model_config = _MODEL_CONFIG

    explanation: str = Field(min_length=1, max_length=_MAX_EXPLANATION_CHARS)
    generated: bool
    prompt_version: str = Field(alias="promptVersion")


def normalize_number(raw: str) -> Decimal:
    """Normalize a numeric token to Decimal.

    Thousands separators and a trailing percent sign are removed, so `2,800`,
    `2800` and `87%` all normalize to comparable Decimal values.
    """

    return Decimal(raw.replace(",", "").rstrip("%"))


def extract_numbers(text: str) -> frozenset[Decimal]:
    """Return every numeric value mentioned in a generated explanation."""

    return frozenset(normalize_number(match.group()) for match in _NUMBER_PATTERN.finditer(text))


def allowed_numbers(request: ExplainMatchRequest) -> frozenset[Decimal]:
    """Build the set of numbers the explanation is allowed to mention."""

    return frozenset(
        {
            Decimal(request.match_score),
            _to_decimal(request.property.price),
            _to_decimal(request.preferences.budget_max),
            _to_decimal(request.property.distance_km),
            _to_decimal(request.preferences.max_distance_km),
        }
    )


def format_mxn(value: Decimal, currency: str = _DEFAULT_CURRENCY) -> str:
    """Format a price in Mexican style with the currency given by the input."""

    quantized = value.quantize(Decimal("0.01"))
    text = f"{quantized:,.2f}"
    if text.endswith(".00"):
        text = text[:-3]
    return f"${text} {currency}"
