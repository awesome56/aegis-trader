"""Backtest orchestration: creation, execution, persistence, ownership.

Isolated from live trading: the engine only reads historical candles and writes
Backtest/BacktestResult rows. It never touches brokers, orders, positions, cash
or risk state.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.engine import BacktestingEngine
from app.backtesting.exceptions import BacktestValidationError
from app.backtesting.series import downsample_points, monthly_returns
from app.backtesting.types import ENGINE_VERSION, BacktestConfig, BacktestRunResult
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.market.enums import Timeframe
from app.market.services.market_data import MarketDataService
from app.market.validation import normalize_symbol
from app.models.backtest import Backtest, BacktestResult
from app.models.enums import BacktestStatus, NotificationSeverity
from app.notifications.service import CATEGORY_SYSTEM, NotificationService
from app.realtime.events import DomainEvent, queue_event
from app.repositories.backtest import BacktestRepository, BacktestResultRepository
from app.repositories.strategy import StrategyRepository

logger = get_logger(__name__)

MAX_EQUITY_POINTS = 600


def _as_datetimes(start: date, end: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start, time.min, tzinfo=UTC),
        datetime.combine(end, time.max, tzinfo=UTC),
    )


class BacktestService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._backtests = BacktestRepository(session)
        self._results = BacktestResultRepository(session)
        self._strategies = StrategyRepository(session)

    # --- creation -----------------------------------------------------------
    async def create(
        self,
        *,
        user_id: uuid.UUID,
        strategy_id: uuid.UUID,
        symbols: list[str],
        timeframe: str,
        start_date: date,
        end_date: date,
        initial_capital: Decimal,
        position_size_percent: Decimal | None = None,
        fees_pct: Decimal | None = None,
        slippage_pct: Decimal | None = None,
        benchmark_symbol: str | None = None,
        force_close_at_end: bool | None = None,
        name: str | None = None,
    ) -> Backtest:
        settings = self._settings
        if not settings.BACKTEST_ENABLED:
            raise ConflictError("Backtesting is disabled")

        strategy = await self._strategies.get(strategy_id)
        if strategy is None:
            raise NotFoundError(f"Strategy {strategy_id} not found")

        if len(symbols) != 1:
            raise BacktestValidationError("V1 backtests support exactly one symbol")
        symbol = normalize_symbol(symbols[0])
        try:
            tf = Timeframe.parse(timeframe)
        except Exception as exc:  # noqa: BLE001
            raise BacktestValidationError(f"Unsupported timeframe {timeframe!r}") from exc

        if end_date <= start_date:
            raise BacktestValidationError("end_date must be after start_date")
        if initial_capital <= 0:
            raise BacktestValidationError("initial_capital must be greater than 0")
        if (end_date - start_date).days > settings.BACKTEST_MAX_RANGE_DAYS:
            raise BacktestValidationError(
                f"date range exceeds {settings.BACKTEST_MAX_RANGE_DAYS} days"
            )

        active = await self._backtests.count_active_for_user(user_id)
        if active >= settings.BACKTEST_MAX_CONCURRENT_PER_USER:
            raise ConflictError(
                "too many running backtests; wait for one to finish",
                details={"max_concurrent": settings.BACKTEST_MAX_CONCURRENT_PER_USER},
            )

        resolved_position = position_size_percent or Decimal(
            str(settings.BACKTEST_DEFAULT_POSITION_PERCENT)
        )
        resolved_fees = fees_pct if fees_pct is not None else Decimal(
            str(settings.BACKTEST_DEFAULT_COMMISSION_PCT)
        )
        resolved_slippage = slippage_pct if slippage_pct is not None else Decimal(
            str(settings.BACKTEST_DEFAULT_SLIPPAGE_PCT)
        )
        resolved_force_close = (
            force_close_at_end
            if force_close_at_end is not None
            else settings.BACKTEST_FORCE_CLOSE_AT_END
        )
        assumptions = {
            "position_size_percent": str(resolved_position),
            "fees_pct": str(resolved_fees),
            "slippage_pct": str(resolved_slippage),
            "force_close_at_end": resolved_force_close,
            "execution_timing": "next_candle_open",
            "engine_version": ENGINE_VERSION,
        }
        now = datetime.now(UTC)
        backtest = Backtest(
            user_id=user_id,
            strategy_id=strategy.id,
            name=name or f"{strategy.name} — {symbol} {tf.value}",
            symbols=[symbol],
            timeframe=tf.value,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            benchmark_symbol=normalize_symbol(benchmark_symbol) if benchmark_symbol else None,
            status=BacktestStatus.PENDING,
            parameters=assumptions,
            config_snapshot={
                "strategy": {
                    "id": str(strategy.id),
                    "key": strategy.slug,
                    "parameters": strategy.parameters,
                },
                "execution": assumptions,
                "symbol": symbol,
                "timeframe": tf.value,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "initial_capital": str(initial_capital),
                "benchmark_symbol": normalize_symbol(benchmark_symbol)
                if benchmark_symbol
                else None,
            },
            created_at=now,
            updated_at=now,
        )
        await self._backtests.add(backtest)
        self._emit("backtest.created", backtest, user_id)
        return backtest

    # --- execution ----------------------------------------------------------
    async def execute(self, backtest_id: uuid.UUID) -> Backtest:
        backtest = await self._backtests.get_locked(backtest_id)
        if backtest is None:
            raise NotFoundError(f"Backtest {backtest_id} not found")
        if backtest.status is BacktestStatus.COMPLETED:
            return backtest  # idempotent
        if backtest.status is BacktestStatus.CANCELLED:
            return backtest

        now = datetime.now(UTC)
        backtest.status = BacktestStatus.RUNNING
        backtest.started_at = now
        backtest.updated_at = now
        backtest.error = None
        await self._session.flush()
        self._emit("backtest.started", backtest, backtest.user_id)

        try:
            run = await self._run(backtest)
            await self._persist_result(backtest, run)
            backtest.status = BacktestStatus.COMPLETED
            backtest.completed_at = datetime.now(UTC)
            backtest.updated_at = backtest.completed_at
            backtest.error = None
            await self._session.flush()
            self._emit("backtest.completed", backtest, backtest.user_id)
            await self._notify(
                backtest,
                title="Backtest completed",
                message=f"{backtest.name} finished with {run.metrics.total_return_pct}% return.",
                severity=NotificationSeverity.INFO,
            )
            logger.info(
                "backtest_completed",
                backtest_id=str(backtest.id),
                user_id=str(backtest.user_id),
                strategy=run.strategy_key,
                symbol=run.symbol,
                timeframe=backtest.timeframe,
                candles=len(run.equity_curve),
                trades=run.metrics.num_trades,
            )
        except Exception as exc:  # noqa: BLE001 - persist a safe failure reason
            backtest.status = BacktestStatus.FAILED
            backtest.completed_at = datetime.now(UTC)
            backtest.updated_at = backtest.completed_at
            backtest.error = str(exc)[:1000]
            await self._session.flush()
            self._emit("backtest.failed", backtest, backtest.user_id)
            await self._notify(
                backtest,
                title="Backtest failed",
                message=f"{backtest.name} could not be completed.",
                severity=NotificationSeverity.WARNING,
            )
            logger.warning(
                "backtest_failed", backtest_id=str(backtest.id), error=str(exc)
            )
        return backtest

    async def _run(self, backtest: Backtest) -> BacktestRunResult:
        snapshot = backtest.config_snapshot or {}
        strategy_config = snapshot.get("strategy", {})
        strategy_key = strategy_config.get("key")
        if not strategy_key:
            raise BacktestValidationError("backtest has no strategy configuration snapshot")
        symbol = (backtest.symbols or [None])[0]
        if not symbol:
            raise BacktestValidationError("backtest has no symbol")

        assumptions = backtest.parameters or {}
        start_dt, end_dt = _as_datetimes(backtest.start_date, backtest.end_date)
        limit = min(self._settings.BACKTEST_MAX_CANDLES, self._settings.MARKET_MAX_CANDLE_LIMIT)
        market = MarketDataService(self._session, settings=self._settings)

        candles = await market.get_candles(
            symbol, backtest.timeframe, start_dt, end_dt, limit=limit
        )
        benchmark_candles = None
        if backtest.benchmark_symbol:
            benchmark_candles = await market.get_candles(
                backtest.benchmark_symbol, backtest.timeframe, start_dt, end_dt, limit=limit
            )

        config = BacktestConfig(
            strategy_key=strategy_key,
            symbols=[symbol],
            timeframe=backtest.timeframe,
            start=start_dt,
            end=end_dt,
            initial_capital=backtest.initial_capital,
            position_size_percent=Decimal(str(assumptions.get("position_size_percent", "100"))),
            fees_pct=Decimal(str(assumptions.get("fees_pct", "0"))),
            slippage_pct=Decimal(str(assumptions.get("slippage_pct", "0"))),
            force_close_at_end=bool(assumptions.get("force_close_at_end", True)),
            benchmark_symbol=backtest.benchmark_symbol,
        )
        return BacktestingEngine(self._settings).run(
            config, candles, benchmark_candles=benchmark_candles
        )

    async def _persist_result(self, backtest: Backtest, run: BacktestRunResult) -> None:
        existing = await self._results.get_for_backtest(backtest.id)
        row = existing or BacktestResult(backtest_id=backtest.id)
        metrics = run.metrics
        row.initial_capital = metrics.initial_capital
        row.final_capital = metrics.final_capital
        row.total_return_pct = metrics.total_return_pct
        row.benchmark_return_pct = metrics.benchmark_return_pct
        row.num_trades = metrics.num_trades
        row.wins = metrics.wins
        row.losses = metrics.losses
        row.win_rate = metrics.win_rate
        row.average_win = metrics.average_win
        row.average_loss = metrics.average_loss
        row.profit_factor = metrics.profit_factor
        row.max_drawdown_pct = metrics.max_drawdown_pct
        row.sharpe_ratio = metrics.sharpe_ratio
        row.sortino_ratio = metrics.sortino_ratio
        row.expectancy = metrics.expectancy
        row.exposure_pct = metrics.exposure_pct
        row.fees = metrics.total_fees
        row.slippage = metrics.total_slippage
        row.equity_curve = [
            point.model_dump(mode="json")
            for point in downsample_points(run.equity_curve, MAX_EQUITY_POINTS)
        ]
        row.trade_history = [trade.model_dump(mode="json") for trade in run.trades]
        row.metrics = metrics.model_dump(mode="json")
        row.monthly_returns = monthly_returns(run.equity_curve, metrics.initial_capital)
        row.strategy_config = backtest.config_snapshot
        row.engine_version = run.engine_version
        row.updated_at = datetime.now(UTC)
        if existing is None:
            self._session.add(row)
        await self._session.flush()

    # --- reads / cancel -----------------------------------------------------
    async def get(self, user_id: uuid.UUID, backtest_id: uuid.UUID) -> Backtest:
        backtest = await self._backtests.get_for_user(backtest_id, user_id)
        if backtest is None:
            raise NotFoundError(f"Backtest {backtest_id} not found")
        return backtest

    async def list(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[Backtest], int]:
        items = await self._backtests.list_for_user(user_id, limit=limit, offset=offset)
        total = await self._backtests.count_for_user(user_id)
        return items, total

    async def result_for(self, backtest_id: uuid.UUID) -> BacktestResult | None:
        return await self._results.get_for_backtest(backtest_id)

    async def cancel(self, user_id: uuid.UUID, backtest_id: uuid.UUID) -> Backtest:
        backtest = await self._backtests.get_for_user(backtest_id, user_id)
        if backtest is None:
            raise NotFoundError(f"Backtest {backtest_id} not found")
        if backtest.status is BacktestStatus.CANCELLED:
            return backtest
        if backtest.status is not BacktestStatus.PENDING:
            raise ConflictError(
                "only pending backtests can be cancelled",
                details={"status": backtest.status.value},
            )
        now = datetime.now(UTC)
        backtest.status = BacktestStatus.CANCELLED
        backtest.completed_at = now
        backtest.updated_at = now
        await self._session.flush()
        self._emit("backtest.cancelled", backtest, user_id)
        return backtest

    async def strategy_name(self, strategy_id: uuid.UUID | None) -> str | None:
        if strategy_id is None:
            return None
        strategy = await self._strategies.get(strategy_id)
        return strategy.name if strategy else None

    # --- helpers ------------------------------------------------------------
    def _emit(self, event: str, backtest: Backtest, user_id: uuid.UUID | None) -> None:
        queue_event(
            self._session.info,
            DomainEvent(
                event=event,
                data={
                    "backtest_id": str(backtest.id),
                    "status": backtest.status.value,
                    "strategy_id": str(backtest.strategy_id) if backtest.strategy_id else None,
                    "symbols": backtest.symbols or [],
                },
                user_id=user_id,
            ),
        )

    async def _notify(
        self,
        backtest: Backtest,
        *,
        title: str,
        message: str,
        severity: NotificationSeverity,
    ) -> None:
        if backtest.user_id is None:
            return
        await NotificationService(self._session).create_notification(
            user_id=backtest.user_id,
            category=CATEGORY_SYSTEM,
            title=title,
            message=message,
            severity=severity,
            payload={"backtest_id": str(backtest.id)},
        )


def default_range(days: int = 180) -> tuple[date, date]:
    end = datetime.now(UTC).date()
    return end - timedelta(days=days), end
