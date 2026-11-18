"""Protected internal diagnostics: metrics snapshot and readiness detail.

These endpoints never expose prompts, responses, credentials, model ids or vendor
messages. The readiness detail is diagnostic only: the G01 health probes keep their
frozen payload and always answer 200.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from thehouse_genai.api.auth import require_metrics_key
from thehouse_genai.application.budget_port import DailyBudgetPort
from thehouse_genai.application.metrics_port import MetricsRecorder
from thehouse_genai.providers.base import GenerativeAiProvider

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(require_metrics_key)],
)


class _ComponentDetail(BaseModel):
    """Bounded boolean presence flag for one internal component."""

    model_config = ConfigDict(extra="forbid")

    configured: bool


class _BudgetDetail(BaseModel):
    """Bounded budget state; no cost rates, keys or free-form messages."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    exhausted: bool
    resets_at: str


class HealthDetailResponse(BaseModel):
    """Diagnostic counterpart of `/health/ready`; never replaces the probe."""

    model_config = ConfigDict(extra="forbid")

    status: str
    provider: _ComponentDetail
    moderator: _ComponentDetail
    budget: _BudgetDetail


@router.get("/metrics", summary="Internal metrics snapshot")
async def metrics(request: Request) -> dict[str, object]:
    """Return the in-process counters, histograms and gauges as JSON."""

    recorder: MetricsRecorder = request.app.state.metrics
    return recorder.snapshot().to_dict()


@router.get("/health/detail", response_model=HealthDetailResponse, summary="Readiness detail")
async def health_detail(request: Request) -> HealthDetailResponse:
    """Report component presence and budget state with HTTP 200 in every case."""

    provider: GenerativeAiProvider | None = request.app.state.provider
    budget: DailyBudgetPort = request.app.state.budget
    snapshot = budget.snapshot()
    degraded = provider is None or snapshot.exhausted
    return HealthDetailResponse(
        status="degraded" if degraded else "ok",
        provider=_ComponentDetail(configured=provider is not None),
        moderator=_ComponentDetail(configured=bool(request.app.state.moderator_configured)),
        budget=_BudgetDetail(
            enabled=snapshot.enabled,
            exhausted=snapshot.exhausted,
            resets_at=snapshot.resets_at,
        ),
    )
