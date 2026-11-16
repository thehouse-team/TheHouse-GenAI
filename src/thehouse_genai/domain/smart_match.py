"""Domain contracts for smart match explanation."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FactName = Literal[
    "match_score",
    "price",
    "currency",
    "distance_km",
    "services",
    "budget_max",
    "required_services",
    "university",
    "property_title",
    "city",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PropertyInput(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=120)
    price: int | float = Field(gt=0)
    currency: str = Field(min_length=1, max_length=8)
    distance_km: float | None = Field(default=None, ge=0, le=10_000)
    services: list[str] = Field(default_factory=list, max_length=20)
    city: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("services")
    @classmethod
    def _clean_services(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in cleaned:
                cleaned.append(text[:40])
        return cleaned


class UniversityInput(_StrictModel):
    name: str = Field(min_length=1, max_length=120)


class PreferencesInput(_StrictModel):
    budget_max: int | float | None = Field(default=None, gt=0)
    required_services: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("required_services")
    @classmethod
    def _clean_required_services(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in cleaned:
                cleaned.append(text[:40])
        return cleaned


class ExplainMatchRequest(_StrictModel):
    match_score: int = Field(ge=0, le=100)
    property: PropertyInput
    university: UniversityInput | None = None
    preferences: PreferencesInput | None = None

    @model_validator(mode="after")
    def _reject_unnecessary_pii_like_fields(self) -> ExplainMatchRequest:
        # Extra fields are forbidden by schema; this keeps the model explicit.
        return self

    def allowed_numbers(self) -> set[str]:
        values: set[str] = {str(self.match_score)}
        price = self.property.price
        if isinstance(price, float) and price.is_integer():
            values.add(str(int(price)))
        else:
            values.add(str(price))
        if self.property.distance_km is not None:
            dist = self.property.distance_km
            values.add(str(dist))
            if dist.is_integer():
                values.add(str(int(dist)))
        if self.preferences and self.preferences.budget_max is not None:
            budget = self.preferences.budget_max
            if isinstance(budget, float) and budget.is_integer():
                values.add(str(int(budget)))
            else:
                values.add(str(budget))
        return values

    def allowed_services(self) -> set[str]:
        services = {s.casefold() for s in self.property.services}
        if self.preferences:
            services.update(s.casefold() for s in self.preferences.required_services)
        return services


class ExplainMatchResponse(_StrictModel):
    explanation: str = Field(min_length=1, max_length=800)
    facts_used: list[FactName] = Field(min_length=1, max_length=10)

    @field_validator("facts_used")
    @classmethod
    def _unique_facts(cls, value: list[FactName]) -> list[FactName]:
        seen: set[str] = set()
        out: list[FactName] = []
        for item in value:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out


_WORD_RE = re.compile(r"\S+")
_NUMBER_RE = re.compile(r"(?<![A-Za-z_])\d+(?:[.,]\d+)?")
_SERVICE_HINT_RE = re.compile(
    r"\b(alberca|piscina|gym|gimnasio|estacionamiento|parking|"
    r"lavadora|secadora|ac|aire acondicionado)\b",
    re.IGNORECASE,
)


def count_words(text: str) -> int:
    return len(_WORD_RE.findall(text))


def extract_numbers(text: str) -> set[str]:
    return {m.group(0).replace(",", ".") for m in _NUMBER_RE.finditer(text)}


def validate_explanation_fidelity(
    request: ExplainMatchRequest, response: ExplainMatchResponse
) -> None:
    if count_words(response.explanation) > 120:
        raise ValueError("explanation exceeds 120 words")

    # Numbers must come from allowed facts only (score/price/distance/budget).
    allowed = request.allowed_numbers()
    for num in extract_numbers(response.explanation):
        # normalize trailing .0
        normalized = num.rstrip("0").rstrip(".") if "." in num else num
        allowed_norm = {a.rstrip("0").rstrip(".") if "." in a else a for a in allowed}
        if num not in allowed and normalized not in allowed_norm:
            raise ValueError(f"disallowed number in explanation: {num}")

    # Disallow common invented service claims not present in input.
    lower = response.explanation.casefold()
    allowed_services = request.allowed_services()
    for match in _SERVICE_HINT_RE.finditer(lower):
        token = match.group(1).casefold()
        aliases = {
            "alberca": {"alberca", "piscina", "pool"},
            "piscina": {"alberca", "piscina", "pool"},
            "gym": {"gym", "gimnasio"},
            "gimnasio": {"gym", "gimnasio"},
            "estacionamiento": {"estacionamiento", "parking"},
            "parking": {"estacionamiento", "parking"},
            "lavadora": {"lavadora"},
            "secadora": {"secadora"},
            "ac": {"ac", "aire acondicionado", "aire_acondicionado"},
            "aire acondicionado": {"ac", "aire acondicionado", "aire_acondicionado"},
        }.get(token, {token})
        if not (aliases & allowed_services):
            raise ValueError(f"disallowed service claim: {token}")

    # facts_used must be derivable from provided data.
    valid: set[str] = {"match_score"}
    if request.property.title:
        valid.add("property_title")
    if request.property.price is not None:
        valid.update({"price", "currency"})
    if request.property.distance_km is not None:
        valid.add("distance_km")
    if request.property.services:
        valid.add("services")
    if request.property.city:
        valid.add("city")
    if request.university:
        valid.add("university")
    if request.preferences and request.preferences.budget_max is not None:
        valid.add("budget_max")
    if request.preferences and request.preferences.required_services:
        valid.add("required_services")
    for fact in response.facts_used:
        if fact not in valid:
            raise ValueError(f"invalid fact: {fact}")
