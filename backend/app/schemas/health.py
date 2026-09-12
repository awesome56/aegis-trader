"""Health-check schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ComponentState = Literal["healthy", "unhealthy", "not_configured"]


class ComponentHealth(BaseModel):
    name: str
    status: ComponentState
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    service: str
    version: str
    environment: str
    timestamp: datetime
    components: list[ComponentHealth]
