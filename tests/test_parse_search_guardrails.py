"""Evidence-based pruning and deterministic confidence tests."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from thehouse_genai.domain.search_filters import SearchConfidence, SearchFilters
from thehouse_genai.domain.search_guardrails import PrunedField, apply_guardrails


def _candidate(**overrides: Any) -> SearchFilters:
    payload: dict[str, Any] = {
        "maxBudget": None,
        "currency": None,
        "university": None,
        "essentialServices": [],
        "petsAllowed": None,
        "maxDistanceKm": None,
    }
    payload.update(overrides)
    return SearchFilters.model_validate(payload)


def test_every_backed_filter_is_kept_with_high_confidence() -> None:
    query = "Busco cuarto de $3,000 MXN cerca de la UTTT con internet, mascotas y a 2 km"
    candidate = _candidate(
        maxBudget=3000,
        currency="MXN",
        university="UTTT",
        essentialServices=["internet"],
        petsAllowed=True,
        maxDistanceKm=2,
    )

    result = apply_guardrails(candidate, query)

    assert result.filters == candidate
    assert result.pruned == ()
    assert result.grounded == 5
    assert result.confidence is SearchConfidence.HIGH
    assert result.generated is True


def test_invented_values_are_pruned_without_rejecting_the_response() -> None:
    candidate = _candidate(
        maxBudget=9999,
        currency="MXN",
        university="UNAM",
        essentialServices=["internet"],
        petsAllowed=True,
        maxDistanceKm=5,
    )

    result = apply_guardrails(candidate, "Busco habitación")

    assert result.filters == _candidate()
    assert result.pruned == (
        PrunedField.MAX_BUDGET,
        PrunedField.CURRENCY,
        PrunedField.UNIVERSITY,
        PrunedField.ESSENTIAL_SERVICES,
        PrunedField.PETS_ALLOWED,
        PrunedField.MAX_DISTANCE_KM,
    )
    assert result.confidence is SearchConfidence.LOW
    assert result.generated is False


def test_empty_candidate_is_not_pruned_but_is_low_and_not_generated() -> None:
    result = apply_guardrails(_candidate(), "Algo barato por aquí")

    assert result.pruned == ()
    assert result.confidence is SearchConfidence.LOW
    assert result.generated is False


def test_range_uses_the_upper_bound_and_caps_confidence_at_medium() -> None:
    query = "entre 2000 y 3000 cerca de la UTTT"
    candidate = _candidate(maxBudget=3000, currency="MXN", university="UTTT")

    result = apply_guardrails(candidate, query)

    assert result.filters.max_budget == Decimal("3000")
    assert result.is_range is True
    assert result.confidence is SearchConfidence.MEDIUM
    assert result.pruned == ()


def test_range_with_an_invented_upper_bound_is_pruned() -> None:
    result = apply_guardrails(_candidate(maxBudget=5000), "entre 2000 y 3000")

    assert result.filters.max_budget is None
    assert result.pruned == (PrunedField.MAX_BUDGET,)


def test_other_currency_discards_budget_and_lowers_confidence() -> None:
    candidate = _candidate(maxBudget=3000, currency="MXN", university="UTTT")

    result = apply_guardrails(candidate, "Busco por 3000 dólares cerca de la UTTT")

    assert result.has_other_currency is True
    assert result.filters.max_budget is None
    assert result.filters.currency is None
    assert PrunedField.MAX_BUDGET in result.pruned
    assert PrunedField.CURRENCY in result.pruned
    assert result.confidence is SearchConfidence.LOW
    assert result.filters.university == "UTTT"


@pytest.mark.parametrize(
    ("value", "query", "expected"),
    [
        ("UTTT", "cerca de la uttt", True),
        ("UTTT", "cerca de la Universidad Tecnológica de Tula-Tepeji", True),
        ("UNAM", "cerca de la UNAM", True),
        ("UTTT", "Busco habitación", False),
    ],
)
def test_university_grounding(value: str, query: str, expected: bool) -> None:
    result = apply_guardrails(_candidate(university=value), query)

    assert (result.filters.university == value) is expected
    if not expected:
        assert result.pruned == (PrunedField.UNIVERSITY,)


def test_services_use_aliases_and_are_deduped_and_sorted() -> None:
    candidate = SearchFilters.model_construct(
        max_budget=None,
        currency=None,
        university=None,
        essential_services=["internet", "agua", "internet"],
        pets_allowed=None,
        max_distance_km=None,
    )

    result = apply_guardrails(candidate, "Quiero wifi, agua y más agua")

    assert result.filters.essential_services == ["agua", "internet"]
    assert result.pruned == (PrunedField.ESSENTIAL_SERVICES,)


def test_mascotas_are_never_an_essential_service() -> None:
    candidate = SearchFilters.model_construct(
        max_budget=None,
        currency=None,
        university=None,
        essential_services=["mascotas", "internet"],
        pets_allowed=None,
        max_distance_km=None,
    )

    result = apply_guardrails(candidate, "Busco con internet y mascotas")

    assert result.filters.essential_services == ["internet"]
    assert PrunedField.ESSENTIAL_SERVICES in result.pruned


def test_pets_positive_is_kept_and_negative_is_pruned() -> None:
    positive = apply_guardrails(_candidate(petsAllowed=True), "se aceptan mascotas")
    negative = apply_guardrails(_candidate(petsAllowed=True), "sin mascotas")
    false_value = SearchFilters.model_construct(
        max_budget=None,
        currency=None,
        university=None,
        essential_services=[],
        pets_allowed=False,
        max_distance_km=None,
    )

    assert positive.filters.pets_allowed is True
    assert positive.pruned == ()
    assert negative.filters.pets_allowed is None
    assert negative.pruned == (PrunedField.PETS_ALLOWED,)
    assert apply_guardrails(false_value, "con mascotas").filters.pets_allowed is None


def test_distance_must_match_the_mentioned_kilometers() -> None:
    kept = apply_guardrails(_candidate(maxDistanceKm=2), "a menos de 2 km de la UTTT")
    invented = apply_guardrails(_candidate(maxDistanceKm=5), "a 2 km de la UTTT")
    minutes = apply_guardrails(_candidate(maxDistanceKm=10), "a 10 minutos de la uni")

    assert kept.filters.max_distance_km == Decimal("2")
    assert invented.pruned == (PrunedField.MAX_DISTANCE_KM,)
    assert minutes.filters.max_distance_km is None
    assert minutes.pruned == (PrunedField.MAX_DISTANCE_KM,)


@pytest.mark.parametrize(
    ("query", "candidate", "expected"),
    [
        ("Busco habitación", _candidate(), SearchConfidence.LOW),
        ("cerca de la UTTT", _candidate(university="UTTT"), SearchConfidence.MEDIUM),
        (
            "cerca de la UTTT con internet",
            _candidate(university="UTTT", essentialServices=["internet"]),
            SearchConfidence.HIGH,
        ),
        (
            "cerca de la UTTT con internet",
            _candidate(university="UTTT", essentialServices=["internet"], maxBudget=9999),
            SearchConfidence.MEDIUM,
        ),
        (
            "entre 2000 y 3000 cerca de la UTTT con internet",
            _candidate(
                maxBudget=3000,
                currency="MXN",
                university="UTTT",
                essentialServices=["internet"],
            ),
            SearchConfidence.MEDIUM,
        ),
    ],
)
def test_confidence_table(
    query: str, candidate: SearchFilters, expected: SearchConfidence
) -> None:
    assert apply_guardrails(candidate, query).confidence is expected


def test_confidence_never_comes_from_a_model_field() -> None:
    result = apply_guardrails(_candidate(university="UTTT"), "cerca de la UTTT")

    assert result.confidence is SearchConfidence.MEDIUM
    assert "confidence" not in type(result.filters).model_fields
