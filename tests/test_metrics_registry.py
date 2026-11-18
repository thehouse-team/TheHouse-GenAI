"""In-process metrics registry tests.

No test opens a socket, reads a credential or uses a real clock: the registry clock is
injectable and the label vocabulary is closed, so the snapshot cannot carry content.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from thehouse_genai.application.metrics_port import (
    AuthRejectionReason,
    CallOutcome,
    EndpointPath,
    GeneratedFlag,
    HttpMethod,
    MetricName,
    MetricsRecorder,
    ProviderErrorCode,
    StatusClass,
    StatusCode,
    TokenDirection,
)
from thehouse_genai.infrastructure.metrics import MetricsRegistry

_REQUEST = {
    "method": HttpMethod.GET,
    "path": EndpointPath.LIVE,
    "status_code": StatusCode.OK,
}
_LATENCY = {
    "method": HttpMethod.POST,
    "path": EndpointPath.EXPLAIN_MATCH,
    "status_class": StatusClass.SUCCESS,
}


def test_registry_satisfies_the_recorder_protocol() -> None:
    assert isinstance(MetricsRegistry(), MetricsRecorder)


def test_registry_starts_empty() -> None:
    snapshot = MetricsRegistry().snapshot()

    assert snapshot.counters == ()
    assert snapshot.histograms == ()
    assert snapshot.uptime_seconds >= 0
    assert snapshot.generated_at.endswith("Z")


def test_injectable_clock_controls_uptime() -> None:
    clock = {"now": 100.0}
    registry = MetricsRegistry(clock=lambda: clock["now"])

    assert registry.snapshot().uptime_seconds == 0.0
    clock["now"] = 105.5
    assert registry.snapshot().uptime_seconds == 5.5


def test_increment_records_one_counter() -> None:
    registry = MetricsRegistry()

    registry.increment(MetricName.HTTP_REQUESTS_TOTAL, **_REQUEST)

    snapshot = registry.snapshot()
    assert len(snapshot.counters) == 1
    counter = snapshot.counters[0]
    assert counter.name == "http_requests_total"
    assert counter.value == 1
    assert dict(counter.labels) == {
        "method": "GET",
        "path": "/health/live",
        "status_code": "200",
    }


def test_increment_accumulates_per_label_set() -> None:
    registry = MetricsRegistry()

    registry.increment(MetricName.HTTP_REQUESTS_TOTAL, **_REQUEST)
    registry.increment(MetricName.HTTP_REQUESTS_TOTAL, **_REQUEST)
    registry.increment(
        MetricName.HTTP_REQUESTS_TOTAL,
        method=HttpMethod.GET,
        path=EndpointPath.LIVE,
        status_code=StatusCode.UNAUTHORIZED,
    )

    assert sorted(counter.value for counter in registry.snapshot().counters) == [1, 2]


def test_increment_accepts_a_counter_without_labels() -> None:
    registry = MetricsRegistry()

    registry.increment(MetricName.RATE_LIMIT_REJECTIONS_TOTAL)

    assert registry.snapshot().counters[0].labels == ()


def test_increment_rejects_unknown_metric() -> None:
    registry = MetricsRegistry()

    with pytest.raises(ValueError, match="unknown counter"):
        registry.increment("not_a_metric")


def test_increment_rejects_a_histogram_name() -> None:
    registry = MetricsRegistry()

    with pytest.raises(ValueError, match="not a counter"):
        registry.increment(MetricName.HTTP_REQUEST_DURATION_MS)


@pytest.mark.parametrize(
    "labels",
    [
        {},
        {"method": HttpMethod.GET, "path": EndpointPath.LIVE},
        {**_REQUEST, "extra": "unexpected"},
        {**_REQUEST, "status_code": "999"},
        {**_REQUEST, "method": "GET "},
    ],
)
def test_increment_rejects_invalid_labels(labels: dict[str, str]) -> None:
    registry = MetricsRegistry()

    with pytest.raises(ValueError):
        registry.increment(MetricName.HTTP_REQUESTS_TOTAL, **labels)

    assert registry.snapshot().counters == ()


def test_rejected_label_value_is_not_echoed() -> None:
    registry = MetricsRegistry()
    rejected_value = "value-that-must-not-appear"

    with pytest.raises(ValueError) as exc_info:
        registry.increment(
            MetricName.HTTP_REQUESTS_TOTAL,
            method=HttpMethod.GET,
            path=EndpointPath.LIVE,
            status_code=rejected_value,
        )

    assert rejected_value not in str(exc_info.value)


def test_closed_enums_are_accepted_as_labels() -> None:
    registry = MetricsRegistry()

    registry.increment(MetricName.PROVIDER_ERRORS_TOTAL, code=ProviderErrorCode.PROVIDER_TIMEOUT)
    registry.increment(MetricName.EXPLAIN_MATCH_OUTCOMES_TOTAL, generated=GeneratedFlag.FALSE)
    registry.increment(MetricName.AUTH_REJECTIONS_TOTAL, reason=AuthRejectionReason.MISSING_KEY)
    registry.increment(MetricName.PROVIDER_TOKENS_TOTAL, direction=TokenDirection.INPUT)

    snapshot = registry.snapshot()
    assert [counter.name for counter in snapshot.counters] == [
        "auth_rejections_total",
        "explain_match_outcomes_total",
        "provider_errors_total",
        "provider_tokens_total",
    ]
    assert dict(snapshot.counters[3].labels) == {"direction": "input"}


def test_snapshot_is_sorted_by_name_and_labels() -> None:
    registry = MetricsRegistry()

    registry.increment(MetricName.PROVIDER_TOKENS_TOTAL, direction=TokenDirection.OUTPUT)
    registry.increment(MetricName.PROVIDER_TOKENS_TOTAL, direction=TokenDirection.INPUT)

    directions = [dict(counter.labels)["direction"] for counter in registry.snapshot().counters]
    assert directions == ["input", "output"]


def test_observe_rejects_unknown_metric_and_wrong_family() -> None:
    registry = MetricsRegistry()

    with pytest.raises(ValueError, match="unknown histogram"):
        registry.observe("not_a_metric", 10)
    with pytest.raises(ValueError, match="not a histogram"):
        registry.observe(MetricName.PROVIDER_CALLS_TOTAL, 10)


def test_observe_rejects_invalid_labels_and_negative_latency() -> None:
    registry = MetricsRegistry()

    with pytest.raises(ValueError, match="expects labels"):
        registry.observe(MetricName.HTTP_REQUEST_DURATION_MS, 10, method=HttpMethod.GET)
    with pytest.raises(ValueError, match="negative"):
        registry.observe(MetricName.HTTP_REQUEST_DURATION_MS, -1, **_LATENCY)

    assert registry.snapshot().histograms == ()


def test_histogram_counts_buckets_and_overflow() -> None:
    registry = MetricsRegistry()

    for value in (30, 60, 120, 240, 600, 1500, 20_000):
        registry.observe(MetricName.HTTP_REQUEST_DURATION_MS, value, **_LATENCY)

    histogram = registry.snapshot().histograms[0]
    buckets = dict(histogram.buckets)
    assert histogram.count == 7
    assert buckets == {
        "50": 1,
        "100": 2,
        "250": 4,
        "500": 4,
        "1000": 5,
        "2000": 6,
        "5000": 6,
        "10000": 6,
        "+Inf": 7,
    }


def test_histogram_percentiles_with_known_data() -> None:
    registry = MetricsRegistry()

    for value in (30, 60, 120, 240, 600, 1500):
        registry.observe(MetricName.HTTP_REQUEST_DURATION_MS, value, **_LATENCY)

    histogram = registry.snapshot().histograms[0]
    assert histogram.total_ms == 2550.0
    assert histogram.mean_ms == 425.0
    assert histogram.p50_ms_approx == 175.0
    assert histogram.p95_ms_approx == 1700.0


def test_histogram_labels_include_the_closed_status_class() -> None:
    registry = MetricsRegistry()

    registry.observe(MetricName.HTTP_REQUEST_DURATION_MS, 120, **_LATENCY)

    histogram = registry.snapshot().histograms[0]
    assert dict(histogram.labels)["status_class"] == "2xx"


def test_single_observation_stays_inside_its_bucket() -> None:
    registry = MetricsRegistry()

    registry.observe(MetricName.HTTP_REQUEST_DURATION_MS, 10, **_LATENCY)

    histogram = registry.snapshot().histograms[0]
    assert histogram.p50_ms_approx == 25.0
    assert histogram.p95_ms_approx == 47.5


def test_snapshot_is_frozen_and_independent() -> None:
    registry = MetricsRegistry()
    registry.increment(MetricName.HTTP_REQUESTS_TOTAL, **_REQUEST)
    first = registry.snapshot()

    with pytest.raises(FrozenInstanceError):
        first.generated_at = "changed"  # type: ignore[misc]
    data = first.to_dict()
    cast(list[dict[str, object]], data["counters"]).clear()

    registry.increment(MetricName.HTTP_REQUESTS_TOTAL, **_REQUEST)

    assert len(first.counters) == 1
    assert first.counters[0].value == 1
    assert len(registry.snapshot().counters) == 1
    assert registry.snapshot().counters[0].value == 2


def test_snapshot_is_strict_json() -> None:
    registry = MetricsRegistry()
    registry.increment(MetricName.HTTP_REQUESTS_TOTAL, **_REQUEST)
    registry.observe(MetricName.HTTP_REQUEST_DURATION_MS, 120, **_LATENCY)

    raw = registry.snapshot().to_json()
    payload = json.loads(raw)

    assert payload["schema_version"] == "1"
    assert payload["counters"][0]["value"] == 1
    assert payload["histograms"][0]["p95_ms_approx"] > 0
    assert "Infinity" not in raw
    assert "NaN" not in raw


def test_concurrent_increments_are_atomic() -> None:
    registry = MetricsRegistry()

    def worker(_index: int) -> None:
        for _ in range(100):
            registry.increment(MetricName.PROVIDER_CALLS_TOTAL, outcome=CallOutcome.SUCCESS)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(worker, range(8)))

    assert registry.snapshot().counters[0].value == 800


def test_concurrent_observations_are_atomic() -> None:
    registry = MetricsRegistry()

    def worker(_index: int) -> None:
        for _ in range(50):
            registry.observe(MetricName.HTTP_REQUEST_DURATION_MS, 10, **_LATENCY)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(worker, range(8)))

    histogram = registry.snapshot().histograms[0]
    assert histogram.count == 400
    assert dict(histogram.buckets)["50"] == 400
