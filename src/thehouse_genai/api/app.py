"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from thehouse_genai import __version__
from thehouse_genai.api.errors import install_exception_handlers
from thehouse_genai.api.middleware import (
    RequestContextMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from thehouse_genai.api.rate_limit import InMemoryRateLimiter
from thehouse_genai.api.routes import generative, health
from thehouse_genai.domain.moderation import MAX_TEXT_CHARS as MODERATION_MAX_TEXT_CHARS
from thehouse_genai.domain.moderation import ModerationDecision
from thehouse_genai.infrastructure.config import Settings, get_settings
from thehouse_genai.infrastructure.logging import configure_logging
from thehouse_genai.infrastructure.metrics import MetricsRegistry
from thehouse_genai.providers.base import GenerativeAiProvider
from thehouse_genai.providers.factory import (
    ProviderConfigurationError,
    UnsupportedProviderError,
    build_provider,
)
from thehouse_genai.providers.moderation import (
    GuardedModerationProvider,
    LocalRuleModerator,
    ModerationProvider,
    ModerationRequest,
    ModerationResponse,
)

logger = logging.getLogger(__name__)


class _BlockingModerator:
    """Fail-closed moderator used when the local moderator cannot be built."""

    async def check(self, request: ModerationRequest) -> ModerationResponse:
        """Block every completion; no text is ever returned unchecked."""

        return ModerationResponse(decision=ModerationDecision.BLOCK)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application from explicit settings or the environment."""

    resolved = settings or get_settings()
    configure_logging(resolved.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger.info("app.startup", extra={"environment": resolved.app_env})
        yield
        logger.info("app.shutdown", extra={"environment": resolved.app_env})

    expose_docs = resolved.app_env in {"local", "test"}
    app = FastAPI(
        title="TheHouse GenAI",
        version=__version__,
        docs_url="/docs" if expose_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if expose_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved
    metrics = MetricsRegistry()
    app.state.metrics = metrics
    app.state.rate_limiter = InMemoryRateLimiter(
        requests=resolved.rate_limit_requests,
        window_seconds=resolved.rate_limit_window_seconds,
        max_clients=resolved.rate_limit_max_clients,
    )

    try:
        provider: GenerativeAiProvider | None = build_provider(resolved)
    except (UnsupportedProviderError, ProviderConfigurationError):
        logger.error("provider.not_configured")
        provider = None
    app.state.provider = provider

    try:
        moderation_provider: ModerationProvider = GuardedModerationProvider(
            LocalRuleModerator(),
            timeout_seconds=resolved.genai_timeout_seconds,
            max_text_chars=MODERATION_MAX_TEXT_CHARS,
        )
    except Exception:
        logger.error("moderation.not_configured")
        moderation_provider = _BlockingModerator()
    app.state.moderation_provider = moderation_provider

    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=resolved.max_request_bytes)
    app.add_middleware(RequestContextMiddleware, metrics=metrics)
    if resolved.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Service-Key"],
        )
    # Added last so it wraps every other middleware, including the size limiter.
    app.add_middleware(SecurityHeadersMiddleware)

    install_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(generative.router)
    return app
