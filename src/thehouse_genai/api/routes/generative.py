"""Generative endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from thehouse_genai.api.security import require_service_auth
from thehouse_genai.application.explain_match import ExplainSmartMatchUseCase
from thehouse_genai.domain.smart_match import ExplainMatchRequest, ExplainMatchResponse
from thehouse_genai.infrastructure.config import Settings, get_settings
from thehouse_genai.providers.base import (
    ProviderAuthError,
    ProviderInputTooLargeError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from thehouse_genai.providers.factory import UnsupportedProviderError, build_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/generative", tags=["generative"])


def _get_use_case(request: Request) -> ExplainSmartMatchUseCase:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    try:
        provider = build_provider(settings)
    except UnsupportedProviderError as exc:
        # Missing provider/credential is a safe service configuration/runtime state.
        logger.warning(
            "smart_match.provider_unavailable",
            extra={"event": "provider_unavailable", "provider": settings.genai_provider},
        )
        raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE") from exc
    return ExplainSmartMatchUseCase(provider)


@router.post(
    "/explain-match",
    response_model=ExplainMatchResponse,
    summary="Explain a precomputed smart match score",
)
async def explain_match(
    payload: ExplainMatchRequest,
    _auth: Annotated[None, Depends(require_service_auth)],
    use_case: Annotated[ExplainSmartMatchUseCase, Depends(_get_use_case)],
) -> ExplainMatchResponse:
    try:
        return await use_case.execute(payload)
    except ProviderInputTooLargeError as exc:
        raise HTTPException(status_code=422, detail="VALIDATION_ERROR") from exc
    except ProviderAuthError as exc:
        logger.warning(
            "smart_match.provider_auth_error",
            extra={"event": "provider_error", "type": "auth"},
        )
        raise HTTPException(status_code=502, detail="PROVIDER_ERROR") from exc
    except ProviderRateLimitError as exc:
        logger.warning(
            "smart_match.provider_rate_limit",
            extra={"event": "provider_error", "type": "rate_limit"},
        )
        raise HTTPException(status_code=429, detail="TOO_MANY_REQUESTS") from exc
    except ProviderTimeoutError as exc:
        logger.warning(
            "smart_match.provider_timeout",
            extra={"event": "provider_error", "type": "timeout"},
        )
        raise HTTPException(status_code=504, detail="PROVIDER_TIMEOUT") from exc
    except ProviderInvalidResponseError as exc:
        logger.warning(
            "smart_match.provider_invalid",
            extra={"event": "provider_error", "type": "invalid"},
        )
        raise HTTPException(status_code=502, detail="PROVIDER_ERROR") from exc
    except ProviderUnavailableError as exc:
        logger.warning(
            "smart_match.provider_unavailable",
            extra={"event": "provider_error", "type": "unavailable"},
        )
        raise HTTPException(status_code=503, detail="SERVICE_UNAVAILABLE") from exc
