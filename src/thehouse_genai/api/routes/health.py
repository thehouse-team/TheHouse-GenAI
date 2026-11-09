"""Health probe endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from thehouse_genai import __version__

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Stable health payload shared by liveness and readiness probes."""

    status: str = "ok"
    service: str = "thehouse-genai"
    version: str = __version__


@router.get("/live", response_model=HealthResponse, summary="Liveness probe")
async def live() -> HealthResponse:
    """Report that the process is running."""

    return HealthResponse()


@router.get("/ready", response_model=HealthResponse, summary="Readiness probe")
async def ready() -> HealthResponse:
    """Report that configuration loaded and the service can accept traffic.

    G01 has no external dependencies; future specs must extend readiness with only
    bounded, non-critical checks.
    """

    return HealthResponse()
