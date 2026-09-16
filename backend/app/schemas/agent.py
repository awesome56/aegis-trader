"""Agent API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import AgentMode, MarketRegime, OrderAction, RunStatus


class AgentEvidenceSchema(BaseModel):
    type: str
    source: str
    direction: str | None = None
    confidence: Decimal | None = None
    data: dict = Field(default_factory=dict)


class AgentRunSchema(BaseModel):
    id: uuid.UUID
    status: RunStatus
    provider: str | None
    model: str | None
    mode: AgentMode
    symbols: list[str]
    prompt: str | None
    error: str | None
    latency_ms: int | None
    tokens_used: int | None
    usage: dict | None
    proposal_id: uuid.UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AgentRunCreateRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(default="1h", max_length=16)
    mode: AgentMode = AgentMode.ANALYSIS_ONLY
    provider_config_id: uuid.UUID | None = None
    broker_account_id: uuid.UUID | None = None
    prompt: str | None = Field(default=None, max_length=2000)


class AgentDecisionSchema(BaseModel):
    id: uuid.UUID
    agent_run_id: uuid.UUID | None
    symbol: str
    action: OrderAction
    confidence: Decimal
    reasoning_summary: str | None
    evidence: list[dict] | None
    concerns: list[str] | None
    proposal_recommended: bool
    market_regime: MarketRegime | None
    strategy_signal_ids: list | None
    proposal_id: uuid.UUID | None
    created_at: datetime


class AgentRunPageSchema(BaseModel):
    items: list[AgentRunSchema]
    total: int
    page: int
    page_size: int


class AgentDecisionPageSchema(BaseModel):
    items: list[AgentDecisionSchema]
    total: int
    page: int
    page_size: int


class AgentStatusSchema(BaseModel):
    enabled: bool
    default_mode: str
    provider: str | None
    model: str | None
    provider_status: str
    provider_config_id: str | None
    running: int
    runs_today: int
    recent_failures: int
    last_run: dict | None
