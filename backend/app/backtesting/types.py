"""Typed backtest contracts.

All monetary values are :class:`~decimal.Decimal`. These types are IO-free so
they can be unit-tested without a database or provider.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

ENGINE_VERSION = "phase8-v1"


class BacktestAction(StrEnum):
    NONE = "NONE"
    OPEN_LONG = "OPEN_LONG"
    CLOSE_LONG = "CLOSE_LONG"


class BacktestExitReason(StrEnum):
    SIGNAL = "SIGNAL"
    END_OF_BACKTEST = "END_OF_BACKTEST"


class BacktestConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy_key: str
    symbols: list[str] = Field(min_length=1)
    timeframe: str
    start: AwareDatetime
    end: AwareDatetime
    initial_capital: Decimal = Field(gt=0)
    position_size_percent: Decimal = Field(default=Decimal("100"), gt=0, le=100)
    fees_pct: Decimal = Field(default=Decimal("0"), ge=0)
    slippage_pct: Decimal = Field(default=Decimal("0"), ge=0)
    max_open_positions: int = Field(default=1, ge=1)
    force_close_at_end: bool = True
    benchmark_symbol: str | None = None


class BacktestTradeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    side: str
    quantity: Decimal
    entry_time: AwareDatetime
    entry_price: Decimal
    exit_time: AwareDatetime
    exit_price: Decimal
    gross_pnl: Decimal
    fees: Decimal
    slippage: Decimal
    net_pnl: Decimal
    return_pct: Decimal
    holding_period_seconds: int
    exit_reason: BacktestExitReason


class BacktestEquityPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: AwareDatetime
    cash: Decimal
    positions_value: Decimal
    equity: Decimal
    cumulative_return_pct: Decimal
    drawdown_pct: Decimal


class BacktestMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class BacktestRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    engine_version: str = ENGINE_VERSION
    strategy_key: str
    symbol: str
    config: BacktestConfig
    metrics: BacktestMetrics
    equity_curve: list[BacktestEquityPoint]
    trades: list[BacktestTradeResult]
