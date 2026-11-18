"""Generative endpoints protected by minimal service-key authentication."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from thehouse_genai.api.auth import require_service_key
from thehouse_genai.api.rate_limit import enforce_rate_limit
from thehouse_genai.application.explain_match import EXPLAIN_MATCH_PROMPT_VERSION, ExplainMatch
from thehouse_genai.domain.match_explanation import ExplainMatchRequest, ExplainMatchResponse
from thehouse_genai.providers.base import GenerativeAiProvider

router = APIRouter(
    prefix="/api/v1/generative",
    tags=["generative"],
    dependencies=[Depends(require_service_key), Depends(enforce_rate_limit)],
)


def _get_use_case(request: Request) -> ExplainMatch:
    """Resolve the provider built at startup and bind it to the use case."""

    provider: GenerativeAiProvider | None = request.app.state.provider
    return ExplainMatch(provider, prompt_version=EXPLAIN_MATCH_PROMPT_VERSION)


@router.post(
    "/explain-match",
    response_model=ExplainMatchResponse,
    response_model_by_alias=True,
    summary="Explain a Smart Match score computed by Backend",
)
async def explain_match(
    payload: ExplainMatchRequest,
    use_case: Annotated[ExplainMatch, Depends(_get_use_case)],
) -> ExplainMatchResponse:
    """Return a faithful explanation or a safe template fallback."""

    return await use_case.execute(payload)
