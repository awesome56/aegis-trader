"""Phase 10 schemas: broker connections + auto-trading policy."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import BrokerEnvironment, ProviderStatus


class BrokerConnectionCreateRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    environment: BrokerEnvironment
    account_external_id: str | None = Field(default=None, max_length=255)
    api_key: str | None = Field(default=None, max_length=512)
    api_secret: str | None = Field(default=None, max_length=512)
    access_token: str | None = Field(default=None, max_length=1024)
    enabled: bool = True
    make_default: bool = False


class BrokerConnectionUpdateRequest(BaseModel):
    account_external_id: str | None = Field(default=None, max_length=255)
    api_key: str | None = Field(default=None, max_length=512)
    api_secret: str | None = Field(default=None, max_length=512)
    access_token: str | None = Field(default=None, max_length=1024)
    enabled: bool | None = None


class BrokerConnectionSchema(BaseModel):
    id: uuid.UUID
    provider: str
    environment: BrokerEnvironment
    account_external_id: str | None
    configured: bool
    api_key_masked: str | None
    enabled: bool
    is_default: bool
    status: ProviderStatus
    last_tested_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class BrokerConnectionTestResponse(BaseModel):
    ok: bool
    status: str
    detail: str | None = None


class AutoTradingPolicySchema(BaseModel):
    id: uuid.UUID | None = None
    broker_account_id: uuid.UUID | None = None
    environment: BrokerEnvironment
    enabled: bool
    allow_open: bool
    allow_add: bool
    allow_reduce: bool
    allow_close: bool
    allow_cancel: bool
    allow_replace: bool
    allow_manage_manual_positions: bool
    allow_manage_manual_orders: bool
    allowed_asset_classes: list | None = None
    allowed_symbols: list | None = None
    max_trade_notional: Decimal | None = None
    max_position_notional: Decimal | None = None
    max_trades_per_day: int | None = None
    cooldown_seconds: int = 0
    min_agent_confidence: Decimal | None = None
    require_strategy_signal: bool = False
    min_strategy_confidence: Decimal | None = None
    notes: str | None = None


class AutoTradingPolicyUpdateRequest(BaseModel):
    allow_open: bool | None = None
    allow_add: bool | None = None
    allow_reduce: bool | None = None
    allow_close: bool | None = None
    allow_cancel: bool | None = None
    allow_replace: bool | None = None
    allow_manage_manual_positions: bool | None = None
    allow_manage_manual_orders: bool | None = None
    allowed_asset_classes: list[str] | None = None
    allowed_symbols: list[str] | None = None
    max_trade_notional: Decimal | None = None
    max_position_notional: Decimal | None = None
    max_trades_per_day: int | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0)
    min_agent_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    require_strategy_signal: bool | None = None
    min_strategy_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    notes: str | None = Field(default=None, max_length=500)


class AutoTradingEnableRequest(BaseModel):
    confirm: bool = False
    phrase: str | None = Field(default=None, max_length=64)


class AutoTradingAccountStatus(BaseModel):
    broker_account_id: uuid.UUID
    provider: str
    account_name: str
    environment: BrokerEnvironment
    enabled: bool
    trading_state: str
    policy: AutoTradingPolicySchema


class AutoTradingStatusSchema(BaseModel):
    live_trading_allowed: bool
    demo_any_enabled: bool
    live_any_enabled: bool
    accounts: list[AutoTradingAccountStatus]
