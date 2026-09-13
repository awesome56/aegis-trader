"""Deterministic backtesting engine.

Reuses the **same** strategy implementations (Phase 5) and regime + indicators
(Phase 2) as live evaluation. It is fully isolated from brokers, risk, orders
and portfolio state: it only consumes historical ``Candle``s and produces a
:class:`BacktestRunResult`.

Execution timing (documented): a signal evaluated from the completed candle at
index ``i`` is executed at the **open of candle ``i + 1``**. When no next candle
exists the signal is not executed. Long-only V1: LONG opens a long, SHORT closes
an existing long; NEUTRAL is ignored.
"""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal

from app.backtesting import costs
from app.backtesting.exceptions import (
    BacktestDataError,
    BacktestInsufficientData,
    BacktestValidationError,
)
from app.backtesting.metrics import compute_metrics
from app.backtesting.types import (
    ENGINE_VERSION,
    BacktestAction,
    BacktestConfig,
    BacktestEquityPoint,
    BacktestExitReason,
    BacktestRunResult,
    BacktestTradeResult,
)
from app.core.config import Settings, get_settings
from app.market.domain.models import Candle, MarketQuote
from app.market.enums import Timeframe
from app.models.enums import SignalDirection
from app.strategies.regime import MarketRegimeService
from app.strategies.registry import build
from app.strategies.types import StrategyContext

HUNDRED = Decimal("100")
_SECONDS_PER_YEAR = 365 * 24 * 3600


class BacktestingEngine:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def run(
        self,
        config: BacktestConfig,
        candles: list[Candle],
        *,
        benchmark_candles: list[Candle] | None = None,
    ) -> BacktestRunResult:
        if len(config.symbols) > 1:
            raise BacktestValidationError(
                "Multi-symbol backtests are not supported in V1; supply a single symbol"
            )
        symbol = config.symbols[0].strip().upper()
        timeframe = Timeframe.parse(config.timeframe)
        series = _validate_series(candles, symbol)

        strategy = build(config.strategy_key, self._settings)
        regime_service = MarketRegimeService(self._settings)
        warmup = max(strategy.min_candles, regime_service.min_candles)
        if len(series) <= warmup:
            raise BacktestInsufficientData(
                f"need more than {warmup} candles for {config.strategy_key}; got {len(series)}"
            )

        cash = config.initial_capital
        quantity = Decimal("0")
        entry_price = Decimal("0")
        entry_time = series[0].open_time
        entry_fee = Decimal("0")
        entry_slippage = Decimal("0")
        trades: list[BacktestTradeResult] = []
        equity_points: list[BacktestEquityPoint] = []
        exposure_periods = 0
        pending = BacktestAction.NONE
        peak = config.initial_capital

        def close_position(at_time, at_price, reason: BacktestExitReason) -> None:
            nonlocal cash, quantity, entry_fee, entry_slippage
            fill = costs.apply_slippage(at_price, side="SELL", slippage_pct=config.slippage_pct)
            proceeds = quantity * fill
            fee = costs.commission_for(proceeds, config.fees_pct)
            exit_slippage = (at_price - fill) * quantity
            cash += proceeds - fee
            gross = (fill - entry_price) * quantity
            net = gross - entry_fee - fee
            cost_basis = entry_price * quantity
            trades.append(
                BacktestTradeResult(
                    symbol=symbol,
                    side="LONG",
                    quantity=quantity,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=at_time,
                    exit_price=fill,
                    gross_pnl=gross,
                    fees=entry_fee + fee,
                    slippage=entry_slippage + exit_slippage,
                    net_pnl=net,
                    return_pct=(net / cost_basis * HUNDRED) if cost_basis else Decimal("0"),
                    holding_period_seconds=int((at_time - entry_time).total_seconds()),
                    exit_reason=reason,
                )
            )
            quantity = Decimal("0")
            entry_fee = Decimal("0")
            entry_slippage = Decimal("0")

        last_index = len(series) - 1
        for index, candle in enumerate(series):
            if pending is BacktestAction.OPEN_LONG and quantity == 0:
                notional = cash * config.position_size_percent / HUNDRED
                fill = costs.apply_slippage(
                    candle.open, side="BUY", slippage_pct=config.slippage_pct
                )
                quantity = notional / fill if fill > 0 else Decimal("0")
                entry_fee = costs.commission_for(notional, config.fees_pct)
                entry_slippage = (fill - candle.open) * quantity
                cash -= notional + entry_fee
                entry_price = fill
                entry_time = candle.open_time
            elif pending is BacktestAction.CLOSE_LONG and quantity > 0:
                close_position(candle.open_time, candle.open, BacktestExitReason.SIGNAL)
            pending = BacktestAction.NONE

            positions_value = quantity * candle.close
            equity = cash + positions_value
            peak = max(peak, equity)
            drawdown_pct = (peak - equity) / peak * HUNDRED if peak > 0 else Decimal("0")
            equity_points.append(
                BacktestEquityPoint(
                    timestamp=candle.close_time or candle.open_time,
                    cash=cash,
                    positions_value=positions_value,
                    equity=equity,
                    cumulative_return_pct=(
                        (equity - config.initial_capital) / config.initial_capital * HUNDRED
                        if config.initial_capital
                        else Decimal("0")
                    ),
                    drawdown_pct=drawdown_pct,
                )
            )
            if quantity > 0:
                exposure_periods += 1

            if index + 1 <= last_index and index + 1 >= warmup:
                window = series[: index + 1]
                context = self._context(symbol, window)
                outcome = strategy.evaluate(context)
                if outcome.signal is not None:
                    if outcome.signal.direction is SignalDirection.LONG:
                        pending = BacktestAction.OPEN_LONG
                    elif outcome.signal.direction is SignalDirection.SHORT:
                        pending = BacktestAction.CLOSE_LONG

        if quantity > 0 and config.force_close_at_end:
            last = series[-1]
            close_position(
                last.close_time or last.open_time,
                last.close,
                BacktestExitReason.END_OF_BACKTEST,
            )
            equity_points[-1] = equity_points[-1].model_copy(
                update={"cash": cash, "positions_value": Decimal("0"), "equity": cash}
            )

        benchmark_return_pct = _benchmark_return(benchmark_candles)
        periods_per_year = _SECONDS_PER_YEAR / timeframe.seconds
        exposure_pct = Decimal(exposure_periods) / Decimal(len(series)) * HUNDRED
        metrics = compute_metrics(
            initial_capital=config.initial_capital,
            equity_curve=equity_points,
            trades=trades,
            periods_per_year=periods_per_year,
            exposure_pct=exposure_pct,
            benchmark_return_pct=benchmark_return_pct,
        )
        return BacktestRunResult(
            engine_version=ENGINE_VERSION,
            strategy_key=config.strategy_key,
            symbol=symbol,
            config=config,
            metrics=metrics,
            equity_curve=equity_points,
            trades=trades,
        )

    def _context(self, symbol: str, candles: list[Candle]) -> StrategyContext:
        last = candles[-1]
        data_timestamp = last.close_time or last.open_time
        if data_timestamp.tzinfo is None:
            data_timestamp = data_timestamp.replace(tzinfo=UTC)
        regime = MarketRegimeService(self._settings).classify(candles)
        quote = MarketQuote(
            symbol=symbol,
            bid=last.close,
            ask=last.close,
            last=last.close,
            open=last.open,
            high=last.high,
            low=last.low,
            previous_close=candles[-2].close if len(candles) > 1 else last.close,
            volume=last.volume,
            currency=self._settings.MARKET_DEFAULT_CURRENCY,
            provider=last.provider,
            market_timestamp=data_timestamp,
            received_at=data_timestamp,
        )
        return StrategyContext(
            symbol=symbol,
            timeframe=last.timeframe,
            candles=candles,
            quote=quote,
            regime=regime,
            evaluation_time=data_timestamp,
            data_timestamp=data_timestamp,
        )


def _validate_series(candles: list[Candle], symbol: str) -> list[Candle]:
    if not candles:
        raise BacktestDataError("no historical candles available for the requested range")
    ordered = sorted(candles, key=lambda candle: candle.open_time)
    deduped: list[Candle] = []
    seen: set = set()
    for candle in ordered:
        if candle.open_time in seen:
            continue
        seen.add(candle.open_time)
        if candle.high < candle.low:
            raise BacktestDataError(f"invalid candle at {candle.open_time}: high < low")
        deduped.append(candle)
    return deduped


def _benchmark_return(candles: list[Candle] | None) -> Decimal | None:
    if not candles or len(candles) < 2:
        return None
    ordered = sorted(candles, key=lambda candle: candle.open_time)
    first = ordered[0].close
    last = ordered[-1].close
    if first <= 0:
        return None
    return (last - first) / first * HUNDRED
