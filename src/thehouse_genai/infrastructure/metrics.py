"""Thread-safe in-process metrics with bounded labels and a fixed latency histogram.

State is process-local and disappears on restart. All label values come from the closed
enums of the application port: a string that is not in the vocabulary is rejected before
it can reach a counter, so prompts, keys and request IDs can never become labels.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from time import monotonic
from typing import Final

from thehouse_genai.application.metrics_port import (
    LATENCY_BUCKETS_MS,
    OVERFLOW_LABEL,
    AuthRejectionReason,
    CallOutcome,
    CounterSnapshot,
    EndpointPath,
    FallbackReason,
    GaugeSnapshot,
    GeneratedFlag,
    HistogramSnapshot,
    HttpMethod,
    MetricName,
    MetricsRecorder,
    MetricsSnapshot,
    ProviderErrorCode,
    StatusCode,
    TokenDirection,
)
from thehouse_genai.domain.moderation import ModerationCategory, ModerationDecision

type _LabelSpec = Mapping[str, frozenset[str]]
type _MetricKey = tuple[str, tuple[tuple[str, str], ...]]


def _values(enum_type: type[StrEnum]) -> frozenset[str]:
    """Return the closed value set of an enum."""

    return frozenset(str(member.value) for member in enum_type)


_COUNTER_LABELS: Final[dict[MetricName, _LabelSpec]] = {
    MetricName.HTTP_REQUESTS_TOTAL: {
        "method": _values(HttpMethod),
        "path": _values(EndpointPath),
        "status_code": _values(StatusCode),
    },
    MetricName.PROVIDER_CALLS_TOTAL: {"outcome": _values(CallOutcome)},
    MetricName.PROVIDER_ERRORS_TOTAL: {"code": _values(ProviderErrorCode)},
    MetricName.PROVIDER_TOKENS_TOTAL: {"direction": _values(TokenDirection)},
    MetricName.PROVIDER_ESTIMATED_COST: {},
    MetricName.EXPLAIN_MATCH_OUTCOMES_TOTAL: {"generated": _values(GeneratedFlag)},
    MetricName.EXPLAIN_MATCH_FALLBACKS_TOTAL: {"reason": _values(FallbackReason)},
    MetricName.MODERATION_DECISIONS_TOTAL: {"decision": _values(ModerationDecision)},
    MetricName.MODERATION_CATEGORIES_TOTAL: {"category": _values(ModerationCategory)},
    MetricName.AUTH_REJECTIONS_TOTAL: {"reason": _values(AuthRejectionReason)},
    MetricName.RATE_LIMIT_REJECTIONS_TOTAL: {},
    MetricName.BUDGET_EXHAUSTIONS_TOTAL: {},
}

_HISTOGRAM_LABELS: Final[dict[MetricName, _LabelSpec]] = {
    MetricName.HTTP_REQUEST_DURATION_MS: {
        "method": _values(HttpMethod),
        "path": _values(EndpointPath),
    },
}

_GAUGE_NAMES: Final[frozenset[MetricName]] = frozenset({MetricName.PROVIDER_ESTIMATED_COST})


def _normalize_labels(
    metric: str,
    labels: Mapping[str, str],
    spec: _LabelSpec,
) -> tuple[tuple[str, str], ...]:
    """Validate a label set against the spec and return a sorted immutable form.

    Error messages never echo a rejected value, so even a caller mistake cannot put
    request content into an exception that might be logged.
    """

    expected = set(spec)
    received = set(labels)
    if received != expected:
        raise ValueError(f"{metric} expects labels {sorted(expected)}, got {sorted(received)}")
    for name, value in labels.items():
        if value not in spec[name]:
            raise ValueError(f"invalid value for label {name!r} of {metric}")
    return tuple(sorted(labels.items()))


def _percentile(cumulative: list[tuple[int, int]], count: int, quantile: float) -> float:
    """Interpolate a percentile inside the bucket that contains its position."""

    if count <= 0:
        return 0.0
    position = quantile * count
    previous_bound = 0
    previous_cumulative = 0
    for bound, running in cumulative:
        if running >= position:
            in_bucket = running - previous_cumulative
            if in_bucket <= 0:
                return float(bound)
            fraction = (position - previous_cumulative) / in_bucket
            fraction = min(max(fraction, 0.0), 1.0)
            return round(previous_bound + (bound - previous_bound) * fraction, 2)
        previous_bound = bound
        previous_cumulative = running
    return float(cumulative[-1][0])


@dataclass
class _Histogram:
    """Mutable accumulator behind one histogram label set."""

    count: int = 0
    total_ms: float = 0.0
    buckets: dict[int, int] = field(
        default_factory=lambda: {bound: 0 for bound in LATENCY_BUCKETS_MS}
    )
    overflow: int = 0

    def observe(self, value_ms: float) -> None:
        """Add one observation to its bucket."""

        if value_ms < 0:
            raise ValueError("latency must not be negative")
        self.count += 1
        self.total_ms += value_ms
        for bound in LATENCY_BUCKETS_MS:
            if value_ms <= bound:
                self.buckets[bound] += 1
                return
        self.overflow += 1

    def to_snapshot(self, name: str, labels: tuple[tuple[str, str], ...]) -> HistogramSnapshot:
        """Build a frozen summary with cumulative buckets and approximate percentiles."""

        cumulative: list[tuple[str, int]] = []
        running = 0
        for bound in LATENCY_BUCKETS_MS:
            running += self.buckets[bound]
            cumulative.append((str(bound), running))
        running += self.overflow
        cumulative.append((OVERFLOW_LABEL, running))
        finite = [(int(upper), value) for upper, value in cumulative if upper != OVERFLOW_LABEL]
        return HistogramSnapshot(
            name=name,
            labels=labels,
            count=self.count,
            total_ms=round(self.total_ms, 2),
            mean_ms=round(self.total_ms / self.count, 2) if self.count else 0.0,
            p50_ms_approx=_percentile(finite, self.count, 0.50),
            p95_ms_approx=_percentile(finite, self.count, 0.95),
            buckets=tuple(cumulative),
        )


class MetricsRegistry:
    """In-process counters and latency histograms guarded by a short-lived lock."""

    def __init__(self, *, clock: Callable[[], float] | None = None) -> None:
        """Bind an injectable monotonic clock for deterministic uptime assertions."""

        self._clock = clock if clock is not None else monotonic
        self._started = self._clock()
        self._lock = threading.Lock()
        self._counters: dict[_MetricKey, int] = {}
        self._histograms: dict[_MetricKey, _Histogram] = {}
        self._gauges: dict[str, str] = {}

    def increment(self, name: str, *, amount: int = 1, **labels: str) -> None:
        """Add ``amount`` to a counter, or reject an unknown name or label set."""

        if amount < 0:
            raise ValueError("amount must not be negative")
        metric = self._counter_metric(name)
        normalized = _normalize_labels(metric.value, labels, _COUNTER_LABELS[metric])
        key = (metric.value, normalized)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount

    def observe(self, name: str, value_ms: float, **labels: str) -> None:
        """Add one latency observation, or reject an unknown name or label set."""

        if value_ms < 0:
            raise ValueError("latency must not be negative")
        metric = self._histogram_metric(name)
        normalized = _normalize_labels(metric.value, labels, _HISTOGRAM_LABELS[metric])
        key = (metric.value, normalized)
        with self._lock:
            self._histograms.setdefault(key, _Histogram()).observe(value_ms)

    def set_gauge(self, name: str, value: str) -> None:
        """Set a gauge to a validated decimal string, never to free-form text."""

        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("invalid gauge value") from exc
        try:
            metric = MetricName(name)
        except ValueError as exc:
            raise ValueError("unknown gauge") from exc
        if metric not in _GAUGE_NAMES:
            raise ValueError("not a gauge")
        with self._lock:
            self._gauges[metric.value] = str(parsed)

    def snapshot(self) -> MetricsSnapshot:
        """Return a deterministic, immutable view independent of later mutations."""

        with self._lock:
            counters = tuple(
                CounterSnapshot(name=key[0], labels=key[1], value=value)
                for key, value in sorted(self._counters.items())
            )
            histograms = tuple(
                histogram.to_snapshot(key[0], key[1])
                for key, histogram in sorted(self._histograms.items())
            )
            gauges = tuple(
                GaugeSnapshot(name=name, labels=(), value=value)
                for name, value in sorted(self._gauges.items())
            )
            uptime = self._clock() - self._started
        return MetricsSnapshot(
            generated_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            uptime_seconds=round(uptime, 2),
            counters=counters,
            histograms=histograms,
            gauges=gauges,
        )

    @staticmethod
    def _counter_metric(name: str) -> MetricName:
        """Resolve and validate a counter name without echoing unknown input."""

        try:
            metric = MetricName(name)
        except ValueError as exc:
            raise ValueError("unknown counter") from exc
        if metric not in _COUNTER_LABELS:
            raise ValueError("not a counter")
        return metric

    @staticmethod
    def _histogram_metric(name: str) -> MetricName:
        """Resolve and validate a histogram name without echoing unknown input."""

        try:
            metric = MetricName(name)
        except ValueError as exc:
            raise ValueError("unknown histogram") from exc
        if metric not in _HISTOGRAM_LABELS:
            raise ValueError("not a histogram")
        return metric


# Make mypy check the implementation against the application-owned boundary.
_RECORDER: Final[type[MetricsRecorder]] = MetricsRegistry
