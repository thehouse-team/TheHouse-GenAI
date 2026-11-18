"""Structured JSON logging.

Only safe request metadata is logged. Headers, bodies, tokens, API keys and other PII
must never be passed as log fields.

The provider block adds the call metadata of the LLM adapters: the provider, the
internal model id, the error code, the duration and the lengths of the prompt and
the completion. Lengths are metadata, never content. The moderation block adds only
the decision, the category codes and the policy version; never the moderated text.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from thehouse_genai.api.request_context import request_id_ctx

_LOG_EXTRA_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "provider",
    "provider_model",
    "error_code",
    "prompt_chars",
    "completion_chars",
    "generated",
    "prompt_version",
    "fallback_reason",
    "reason",
    "client_id",
    "retry_after_seconds",
    "moderation_decision",
    "moderation_category",
    "policy_version",
)


class RequestIdFilter(logging.Filter):
    """Attach the sanitized request ID from the context to structured records.

    The value is correlation metadata only: it is never part of a provider request, and
    it never overwrites an explicit request ID already set by the caller.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            request_id = request_id_ctx.get()
            if request_id != "-":
                record.request_id = request_id
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _LOG_EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install a single structured stdout handler on the root logger."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Requests are logged once by RequestContextMiddleware with structured fields.
    logging.getLogger("uvicorn.access").disabled = True
    # The HTTP client emits one INFO line per call; keep only our controlled logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Correlate provider and use-case logs with the request that caused them. Filters are
    # installed once per logger so repeated create_app calls do not stack them.
    for name in (
        "thehouse_genai.providers.gemini",
        "thehouse_genai.application.explain_match",
    ):
        target = logging.getLogger(name)
        if not any(isinstance(item, RequestIdFilter) for item in target.filters):
            target.addFilter(RequestIdFilter())
