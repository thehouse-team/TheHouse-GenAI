"""Port and immutable data shapes for process-local operational metrics.

The application layer owns the vocabulary: label values are closed enums and the
snapshot is made of frozen dataclasses. Infrastructure implements the protocol but never
invents new labels, so the public shape stays stable, bounded and PII-free.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol, runtime_checkable

from thehouse_genai.domain.moderation import ModerationCategory, ModerationDecision
from thehouse_genai.domain.search_filters import SearchConfidence
from thehouse_genai.domain.search_guardrails import PrunedField

SNAPSHOT_SCHEMA_VERSION: Final[str] = "1"
LATENCY_BUCKETS_MS: Final[tuple[int, ...]] = (50, 100, 250, 500, 1000, 2000, 5000, 10000)
OVERFLOW_LABEL: Final[str] = "+Inf"


class MetricName(StrEnum):
    """Stable names of every metric recorded in this release."""

    HTTP_REQUESTS_TOTAL = "http_requests_total"
    HTTP_REQUEST_DURATION_MS = "http_request_duration_ms"
    PROVIDER_CALLS_TOTAL = "provider_calls_total"
    PROVIDER_ERRORS_TOTAL = "provider_errors_total"
    PROVIDER_TOKENS_TOTAL = "provider_tokens_total"
    PROVIDER_ESTIMATED_COST = "provider_estimated_cost"
    EXPLAIN_MATCH_OUTCOMES_TOTAL = "explain_match_outcomes_total"
    EXPLAIN_MATCH_FALLBACKS_TOTAL = "explain_match_fallbacks_total"
    PARSE_SEARCH_OUTCOMES_TOTAL = "parse_search_outcomes_total"
    PARSE_SEARCH_CONFIDENCE_TOTAL = "parse_search_confidence_total"
    PARSE_SEARCH_FALLBACKS_TOTAL = "parse_search_fallbacks_total"
    PARSE_SEARCH_PRUNED_FIELDS_TOTAL = "parse_search_pruned_fields_total"
    MODERATION_DECISIONS_TOTAL = "moderation_decisions_total"
    MODERATION_CATEGORIES_TOTAL = "moderation_categories_total"
    AUTH_REJECTIONS_TOTAL = "auth_rejections_total"
    METRICS_AUTH_REJECTIONS_TOTAL = "metrics_auth_rejections_total"
    RATE_LIMIT_REJECTIONS_TOTAL = "rate_limit_rejections_total"
    BUDGET_EXHAUSTIONS_TOTAL = "budget_exhaustions_total"


class HttpMethod(StrEnum):
    """Bounded HTTP methods accepted as a metric label."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    OTHER = "other"


class EndpointPath(StrEnum):
    """Bounded, normalized route names; anything else is grouped as ``other``."""

    LIVE = "/health/live"
    READY = "/health/ready"
    EXPLAIN_MATCH = "/api/v1/generative/explain-match"
    METRICS = "/internal/metrics"
    HEALTH_DETAIL = "/internal/health/detail"
    OTHER = "other"


class StatusCode(StrEnum):
    """Bounded status codes the service can return."""

    OK = "200"
    BAD_REQUEST = "400"
    UNAUTHORIZED = "401"
    FORBIDDEN = "403"
    NOT_FOUND = "404"
    METHOD_NOT_ALLOWED = "405"
    CONFLICT = "409"
    PAYLOAD_TOO_LARGE = "413"
    VALIDATION_ERROR = "422"
    TOO_MANY_REQUESTS = "429"
    INTERNAL_ERROR = "500"
    SERVICE_UNAVAILABLE = "503"
    OTHER = "other"


class StatusClass(StrEnum):
    """Coarse status class for latency series; bounded and free of raw status codes."""

    SUCCESS = "2xx"
    CLIENT_ERROR = "4xx"
    SERVER_ERROR = "5xx"
    OTHER = "other"


class CallOutcome(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class ProviderErrorCode(StrEnum):
    """The closed provider error taxonomy defined in spec 002."""

    PROVIDER_ERROR = "PROVIDER_ERROR"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_AUTH = "PROVIDER_AUTH"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_INVALID_RESPONSE = "PROVIDER_INVALID_RESPONSE"
    PROVIDER_INPUT_TOO_LARGE = "PROVIDER_INPUT_TOO_LARGE"


class TokenDirection(StrEnum):
    INPUT = "input"
    OUTPUT = "output"


class GeneratedFlag(StrEnum):
    TRUE = "true"
    FALSE = "false"


class FallbackReason(StrEnum):
    """Every stable fallback reason, including the budget decision of 007."""

    NO_PROVIDER = "NO_PROVIDER"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_JSON = "INVALID_JSON"
    TOO_LONG = "TOO_LONG"
    MALFORMED_TEXT = "MALFORMED_TEXT"
    NUMBER_NOT_IN_INPUT = "NUMBER_NOT_IN_INPUT"
    SCORE_MISMATCH = "SCORE_MISMATCH"
    UNKNOWN_SERVICE = "UNKNOWN_SERVICE"
    INJECTION_MARKER = "INJECTION_MARKER"
    FOREIGN_CURRENCY = "FOREIGN_CURRENCY"
    FOREIGN_UNIVERSITY = "FOREIGN_UNIVERSITY"
    MODERATION_UNAVAILABLE = "MODERATION_UNAVAILABLE"
    MODERATION_BLOCKED = "MODERATION_BLOCKED"
    MODERATION_REVIEW = "MODERATION_REVIEW"
    INPUT_MODERATION_BLOCKED = "INPUT_MODERATION_BLOCKED"
    INPUT_MODERATION_REVIEW = "INPUT_MODERATION_REVIEW"
    EMPTY_QUERY_AFTER_REDACTION = "EMPTY_QUERY_AFTER_REDACTION"
    ALL_FILTERS_PRUNED = "ALL_FILTERS_PRUNED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


class AuthRejectionReason(StrEnum):
    MISSING_KEY = "missing_key"
    INVALID_KEY = "invalid_key"
    NOT_CONFIGURED = "not_configured"


@dataclass(frozen=True)
class CounterSnapshot:
    """One counter value with its normalized label set."""

    name: str
    labels: tuple[tuple[str, str], ...]
    value: int

    def to_dict(self) -> dict[str, object]:
        """Return a fresh plain dict; callers cannot mutate the snapshot."""

        return {
            "name": self.name,
            "labels": {key: value for key, value in self.labels},
            "value": self.value,
        }


@dataclass(frozen=True)
class GaugeSnapshot:
    """One string-valued gauge, used for exact ``Decimal`` cost values."""

    name: str
    labels: tuple[tuple[str, str], ...]
    value: str

    def to_dict(self) -> dict[str, object]:
        """Return a fresh plain dict."""

        return {
            "name": self.name,
            "labels": {key: value for key, value in self.labels},
            "value": self.value,
        }


@dataclass(frozen=True)
class HistogramSnapshot:
    """A fixed-bucket latency summary with approximate percentiles."""

    name: str
    labels: tuple[tuple[str, str], ...]
    count: int
    total_ms: float
    mean_ms: float
    p50_ms_approx: float
    p95_ms_approx: float
    buckets: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, object]:
        """Return a fresh plain dict with cumulative bucket counts."""

        return {
            "name": self.name,
            "labels": {key: value for key, value in self.labels},
            "count": self.count,
            "total_ms": self.total_ms,
            "mean_ms": self.mean_ms,
            "p50_ms_approx": self.p50_ms_approx,
            "p95_ms_approx": self.p95_ms_approx,
            "buckets": [
                {"upper_bound_ms": upper, "count": value} for upper, value in self.buckets
            ],
        }


@dataclass(frozen=True)
class MetricsSnapshot:
    """An immutable, JSON-serializable view of the registry at one instant."""

    generated_at: str
    uptime_seconds: float
    counters: tuple[CounterSnapshot, ...]
    histograms: tuple[HistogramSnapshot, ...]
    gauges: tuple[GaugeSnapshot, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a fresh plain dict; nested containers are copied too."""

        return {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "uptime_seconds": self.uptime_seconds,
            "counters": [counter.to_dict() for counter in self.counters],
            "histograms": [histogram.to_dict() for histogram in self.histograms],
            "gauges": [gauge.to_dict() for gauge in self.gauges],
        }

    def to_json(self) -> str:
        """Serialize without ``NaN`` or ``Infinity`` so the wire format is strict JSON."""

        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)


@runtime_checkable
class MetricsRecorder(Protocol):
    """Metrics boundary used by the application and the API layer.

    Implementations must reject unknown metric names and label values instead of
    accepting free-form strings, so user data can never become a label.
    """

    def increment(self, name: str, *, amount: int = 1, **labels: str) -> None:
        """Add ``amount`` to a counter; token counters use the reported usage."""

    def observe(self, name: str, value_ms: float, **labels: str) -> None:
        """Add one latency observation to a histogram."""

    def set_gauge(self, name: str, value: str) -> None:
        """Set a string-valued gauge, e.g. an exact ``Decimal`` cost."""

    def snapshot(self) -> MetricsSnapshot:
        """Return an immutable view of all recorded values."""


# Export the moderation enums here so callers need only the port vocabulary.
__all__ = [
    "LATENCY_BUCKETS_MS",
    "OVERFLOW_LABEL",
    "SNAPSHOT_SCHEMA_VERSION",
    "AuthRejectionReason",
    "CallOutcome",
    "CounterSnapshot",
    "EndpointPath",
    "FallbackReason",
    "GaugeSnapshot",
    "GeneratedFlag",
    "HistogramSnapshot",
    "HttpMethod",
    "MetricName",
    "MetricsRecorder",
    "MetricsSnapshot",
    "ModerationCategory",
    "ModerationDecision",
    "ProviderErrorCode",
    "PrunedField",
    "SearchConfidence",
    "StatusClass",
    "StatusCode",
    "TokenDirection",
]
