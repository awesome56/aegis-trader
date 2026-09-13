"""Backtest API schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.backtesting.types import (
    BacktestEquityPoint,
    BacktestMetrics,
    BacktestTradeResult,
)
from app.models.enums import BacktestStatus


class _Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BacktestCreateRequest(BaseModel):
    strategy_id: uuid.UUID
    name: str | None = Field(default=None, max_length=255)
    symbols: list[str] = Field(min_length=1, max_length=10)
    timeframe: str = Field(default="1d", max_length=16)
    start_date: date
    end_date: date
    initial_capital: Decimal = Field(gt=0)
    position_size_percent: Decimal | None = Field(default=None, gt=0, le=100)
    fees_pct: Decimal | None = Field(default=None, ge=0)
    slippage_pct: Decimal | None = Field(default=None, ge=0)
    benchmark_symbol: str | None = Field(default=None, max_length=32)
    force_close_at_end: bool | None = None


class BacktestMetricsSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    initial_capital: Decimal
    final_capital: Decimal
    net_profit: Decimal
    total_return_pct: Decimal
    benchmark_return_pct: Decimal | None
    num_trades: int
    wins: int
    losses: int
    win_rate: Decimal
    average_win: Decimal
    average_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    profit_factor: Decimal | None
    expectancy: Decimal
    max_drawdown: Decimal
    max_drawdown_pct: Decimal
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    total_fees: Decimal
    total_slippage: Decimal
    average_holding_seconds: Decimal
    exposure_pct: Decimal

    @classmethod
    def from_result(cls, result: BacktestMetrics) -> BacktestMetricsSchema:
        return cls(**result.model_dump())


class BacktestSchema(_Schema):
    id: uuid.UUID
    strategy_id: uuid.UUID | None
    strategy_name: str | None = None
    name: str
    symbols: list[str]
    timeframe: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    benchmark_symbol: str | None
    status: BacktestStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    final_capital: Decimal | None = None
    total_return_pct: Decimal | None = None
    max_drawdown_pct: Decimal | None = None
    num_trades: int | None = None


class BacktestPageSchema(BaseModel):
    items: list[BacktestSchema]
    total: int
    page: int
    page_size: int


class EquityCurvePointSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    cash: Decimal
    positions_value: Decimal
    equity: Decimal
    cumulative_return_pct: Decimal
    drawdown_pct: Decimal

    @classmethod
    def from_point(cls, point: BacktestEquityPoint) -> EquityCurvePointSchema:
        return cls(**point.model_dump())


class DrawdownPointSchema(BaseModel):
    timestamp: datetime
    drawdown_pct: Decimal


class BacktestTradeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    side: str
    quantity: Decimal
    entry_time: datetime
    entry_price: Decimal
    exit_time: datetime
    exit_price: Decimal
    gross_pnl: Decimal
    fees: Decimal
    slippage: Decimal
    net_pnl: Decimal
    return_pct: Decimal
    holding_period_seconds: int
    exit_reason: str

    @classmethod
    def from_trade(cls, trade: BacktestTradeResult) -> BacktestTradeSchema:
        return cls(**trade.model_dump())


class BacktestResultSchema(BaseModel):
    backtest_id: uuid.UUID
    engine_version: str | None
    strategy_config: dict | None
    metrics: BacktestMetricsSchema
    equity_curve: list[EquityCurvePointSchema]
    drawdown_curve: list[DrawdownPointSchema]
    monthly_returns: list[dict]
    trades: list[BacktestTradeSchema]
