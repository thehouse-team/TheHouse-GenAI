"""Evidence-based guardrails and deterministic confidence for parsed filters.

The model may only propose filters. Every value is checked against what the student
actually wrote and is dropped when it is not backed by evidence; a single unsupported
filter never rejects the whole response. The resulting field codes are closed so they
can be logged and counted as bounded labels (spec 004, D7 and D10).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from thehouse_genai.domain.search_filters import (
    SearchConfidence,
    SearchFilters,
    chosen_budget,
    extract_distance_km,
    extract_money_evidence,
    extract_pets,
    extract_services,
    has_any_filter,
    is_university_grounded,
)

_MAX_SERVICES: int = 8


class PrunedField(StrEnum):
    """Bounded codes for filters removed for lack of evidence."""

    MAX_BUDGET = "max_budget"
    CURRENCY = "currency"
    UNIVERSITY = "university"
    ESSENTIAL_SERVICES = "essential_services"
    PETS_ALLOWED = "pets_allowed"
    MAX_DISTANCE_KM = "max_distance_km"


@dataclass(frozen=True)
class GuardrailResult:
    """The cleaned filters plus the safe metadata used for logs and metrics."""

    filters: SearchFilters
    pruned: tuple[PrunedField, ...]
    confidence: SearchConfidence
    generated: bool
    grounded: int
    is_range: bool
    has_other_currency: bool


def apply_guardrails(candidate: SearchFilters, query: str) -> GuardrailResult:
    """Keep only the filters backed by the query and compute confidence locally."""

    evidence = extract_money_evidence(query)
    budget = chosen_budget(evidence)
    mentioned_services = set(extract_services(query))
    pets_mentioned = extract_pets(query) is True
    distance_mentioned = extract_distance_km(query)

    pruned: list[PrunedField] = []

    max_budget = candidate.max_budget
    if candidate.max_budget is not None and (budget is None or candidate.max_budget != budget):
        max_budget = None
        pruned.append(PrunedField.MAX_BUDGET)

    currency = candidate.currency
    if candidate.currency is not None and (
        candidate.currency != "MXN" or evidence.has_other_currency or budget is None
    ):
        currency = None
        pruned.append(PrunedField.CURRENCY)

    university = candidate.university
    if candidate.university is not None and not is_university_grounded(
        candidate.university, query
    ):
        university = None
        pruned.append(PrunedField.UNIVERSITY)

    kept_services = {
        service for service in candidate.essential_services if service in mentioned_services
    }
    if len(kept_services) != len(candidate.essential_services):
        pruned.append(PrunedField.ESSENTIAL_SERVICES)
    services = sorted(kept_services)[:_MAX_SERVICES]

    pets_allowed = True if (pets_mentioned and candidate.pets_allowed is True) else None
    if (candidate.pets_allowed is not None and not pets_mentioned) or (
        candidate.pets_allowed is False and pets_mentioned
    ):
        pruned.append(PrunedField.PETS_ALLOWED)

    max_distance_km = candidate.max_distance_km
    if candidate.max_distance_km is not None and candidate.max_distance_km != distance_mentioned:
        max_distance_km = None
        pruned.append(PrunedField.MAX_DISTANCE_KM)

    filters = SearchFilters(
        maxBudget=max_budget,
        currency=currency,
        university=university,
        essentialServices=services,
        petsAllowed=pets_allowed,
        maxDistanceKm=max_distance_km,
    )

    grounded = (
        sum(
            (
                max_budget is not None,
                university is not None,
                pets_allowed is not None,
                max_distance_km is not None,
            )
        )
        + len(services)
    )

    if evidence.has_other_currency or grounded == 0:
        confidence = SearchConfidence.LOW
    elif grounded >= 2 and not pruned and not evidence.is_range:
        confidence = SearchConfidence.HIGH
    else:
        confidence = SearchConfidence.MEDIUM

    return GuardrailResult(
        filters=filters,
        pruned=tuple(pruned),
        confidence=confidence,
        generated=has_any_filter(filters),
        grounded=grounded,
        is_range=evidence.is_range,
        has_other_currency=evidence.has_other_currency,
    )
