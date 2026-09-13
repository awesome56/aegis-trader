"""TradingAnalysisAgent contracts (structured output + run outcomes)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agents.enums import AgentAction, EvidenceType
from app.ai.types import LLMUsage
from app.models.enums import MarketRegime


class AgentEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: EvidenceType | str
    source: str
    direction: str | None = None
    confidence: Decimal | None = None
    data: dict = Field(default_factory=dict)


class ProposedTrade(BaseModel):
    model_config = ConfigDict(frozen=True)

    side: str = Field(pattern="^(BUY|SELL)$")
    order_type: str = "MARKET"
    quantity: Decimal | None = None
    notional: Decimal | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    confidence: Decimal | None = None


class TradingAnalysisResult(BaseModel):
    """Strict structured output. Free-form model prose is never authoritative."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    action: AgentAction
    confidence: Decimal = Field(ge=0, le=1)
    market_regime: MarketRegime | None = None
    summary: str = Field(min_length=1, max_length=4000)
    supporting_evidence: list[AgentEvidence] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    strategy_signals: list[str] = Field(default_factory=list)
    risk_context_summary: str | None = None
    proposal_recommended: bool = False
    proposed_trade: ProposedTrade | None = None

    @field_validator("symbol")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()


class ToolCallRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    ok: bool
    summary: str


class AgentOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: TradingAnalysisResult
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    usage: LLMUsage = Field(default_factory=LLMUsage)
    provider: str
    model: str
    latency_ms: int = 0
    iterations: int = 0
    proposal_id: uuid.UUID | None = None
