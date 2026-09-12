"""StrategyService: orchestrates IO and evaluation.

The service loads enabled strategies, fetches candles/quote, classifies the
regime, builds the :class:`StrategyContext`, runs the pure strategy
implementations, persists de-duplicated signals and returns typed results. It
contains no strategy formulas.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.market.enums import Timeframe
from app.market.services.market_data import MarketDataService
from app.models.enums import SignalDirection
from app.models.strategy import Strategy, StrategySignal
from app.realtime.events import DomainEvent, queue_event
from app.repositories.strategy import StrategyRepository, StrategySignalRepository
from app.strategies.bootstrap import ensure_strategies
from app.strategies.enums import EvaluationStatus
from app.strategies.regime import MarketRegimeService
from app.strategies.registry import build
from app.strategies.types import (
    RegimeAssessment,
    StrategyContext,
    StrategyEvaluationResult,
    StrategySignalResult,
)

logger = get_logger(__name__)

MAX_EVALUATION_CANDLES = 500


class StrategyService:
    def __init__(
        self,
        session: AsyncSession,
        market: MarketDataService,
        *,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._market = market
        self._settings = settings or get_settings()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._strategies = StrategyRepository(session)
        self._signals = StrategySignalRepository(session)
        self._regime = MarketRegimeService(self._settings)

    async def ensure_bootstrapped(self) -> list[Strategy]:
        if not self._settings.STRATEGY_AUTO_BOOTSTRAP:
            return []
        created = await ensure_strategies(self._session, self._settings)
        if created:
            logger.info("strategies_bootstrapped", count=len(created))
        return created

    async def list_strategies(self) -> list[Strategy]:
        return await self._strategies.list_all()

    async def get_strategy(self, strategy_id: uuid.UUID) -> Strategy | None:
        return await self._strategies.get(strategy_id)

    async def strategy_stats(self, strategy_id: uuid.UUID) -> tuple[int, datetime | None]:
        return await self._signals.stats_for_strategy(strategy_id)

    async def set_enabled(self, strategy: Strategy, enabled: bool) -> Strategy:
        strategy.is_enabled = enabled
        now = datetime.now(UTC)
        strategy.updated_at = now
        await self._session.flush()
        event = "strategy.enabled" if enabled else "strategy.disabled"
        queue_event(
            self._session.info,
            DomainEvent(
                event=event,
                data={"strategy": strategy.slug, "name": strategy.name, "enabled": enabled},
            ),
        )
        logger.info("strategy_toggled", strategy=strategy.slug, enabled=enabled)
        return strategy

    async def classify_regime(
        self, symbol: str, timeframe: Timeframe | str | None = None
    ) -> RegimeAssessment:
        tf = Timeframe.parse(timeframe or self._settings.STRATEGY_DEFAULT_TIMEFRAME)
        candles = await self._market.get_latest_candles(
            symbol.upper(), tf, self._regime.min_candles
        )
        return self._regime.classify(candles)

    async def evaluate(
        self,
        symbol: str,
        timeframe: Timeframe | str | None = None,
        *,
        strategy_ids: Sequence[uuid.UUID] | None = None,
        persist: bool = True,
    ) -> list[StrategyEvaluationResult]:
        settings = self._settings
        tf = Timeframe.parse(timeframe or settings.STRATEGY_DEFAULT_TIMEFRAME)
        normalized = symbol.strip().upper()

        enabled = [s for s in await self._strategies.list_all(enabled_only=True)]
        if strategy_ids is not None:
            wanted = {str(sid) for sid in strategy_ids}
            enabled = [s for s in enabled if str(s.id) in wanted]
        if not enabled:
            return []

        implementations = {s.id: build(s.slug, settings) for s in enabled}
        required = max(impl.min_candles for impl in implementations.values())
        limit = min(max(required + 5, 60), settings.MARKET_MAX_CANDLE_LIMIT, MAX_EVALUATION_CANDLES)

        candles = await self._market.get_latest_candles(normalized, tf, limit)
        now = self._clock()
        if not candles:
            return [
                StrategyEvaluationResult(
                    strategy_key=impl.key.value,
                    strategy_name=impl.name,
                    symbol=normalized,
                    timeframe=tf.value,
                    status=EvaluationStatus.INSUFFICIENT_DATA,
                    reason="no candles available",
                )
                for impl in implementations.values()
            ]

        last = candles[-1]
        data_timestamp = last.close_time or last.open_time
        if data_timestamp.tzinfo is None:
            data_timestamp = data_timestamp.replace(tzinfo=UTC)
        age_seconds = max(0.0, (now - data_timestamp).total_seconds())
        allowed_age = tf.seconds * settings.STRATEGY_ANALYSIS_MAX_AGE_MULTIPLIER
        stale = age_seconds > allowed_age

        quote = await self._market.get_quote(normalized)
        asset = await self._market.resolve_asset(normalized)
        regime = self._regime.classify(candles)

        context = StrategyContext(
            symbol=normalized,
            asset_id=asset.id if asset is not None else None,
            timeframe=tf,
            candles=candles,
            quote=quote,
            regime=regime,
            evaluation_time=now,
            data_timestamp=data_timestamp,
        )

        results: list[StrategyEvaluationResult] = []
        for strategy in enabled:
            impl = implementations[strategy.id]
            if stale:
                results.append(
                    StrategyEvaluationResult(
                        strategy_key=impl.key.value,
                        strategy_name=impl.name,
                        symbol=normalized,
                        timeframe=tf.value,
                        status=EvaluationStatus.STALE_DATA,
                        reason=(
                            f"latest candle is {age_seconds:.0f}s old "
                            f"(analysis limit {allowed_age:.0f}s)"
                        ),
                    )
                )
                continue
            outcome = impl.evaluate(context)
            if outcome.status is EvaluationStatus.SIGNAL and outcome.signal is not None:
                if persist:
                    await self._persist_signal(strategy, outcome.signal, context)
                logger.info(
                    "strategy_signal",
                    strategy=strategy.slug,
                    symbol=normalized,
                    timeframe=tf.value,
                    regime=regime.primary.value,
                    direction=outcome.signal.direction.value,
                    confidence=str(outcome.signal.confidence),
                    strength=str(outcome.signal.strength),
                )
            results.append(outcome)
        return results

    async def _persist_signal(
        self,
        strategy: Strategy,
        signal: StrategySignalResult,
        context: StrategyContext,
    ) -> StrategySignal | None:
        duplicate = await self._signals.exists(
            strategy_id=strategy.id,
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            direction=signal.direction,
            data_timestamp=signal.data_timestamp,
        )
        if duplicate:
            return None

        now = self._clock()
        model = StrategySignal(
            strategy_id=strategy.id,
            asset_id=signal.asset_id,
            symbol=signal.symbol,
            direction=signal.direction,
            strength=signal.strength,
            confidence=signal.confidence,
            price=context.quote.last,
            timeframe=signal.timeframe,
            time_horizon=signal.time_horizon,
            market_regime=signal.regime,
            indicators={**signal.indicators, "regime_metrics": context.regime.metrics},
            signal_time=signal.generated_at,
            data_timestamp=signal.data_timestamp,
            expires_at=signal.expires_at,
            created_at=now,
            updated_at=now,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(model)
                await self._session.flush()
        except IntegrityError:
            return None

        queue_event(
            self._session.info,
            DomainEvent(
                event="strategy.signal",
                data={
                    "signal_id": str(model.id),
                    "strategy": strategy.slug,
                    "strategy_name": strategy.name,
                    "symbol": signal.symbol,
                    "direction": signal.direction.value,
                    "strength": str(signal.strength),
                    "confidence": str(signal.confidence),
                    "regime": signal.regime.value,
                    "timeframe": signal.timeframe,
                    "data_timestamp": signal.data_timestamp.isoformat(),
                },
            ),
        )
        return model

    async def list_signals(
        self,
        *,
        strategy_id: uuid.UUID | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        direction: SignalDirection | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StrategySignal]:
        return await self._signals.list_signals(
            strategy_id=strategy_id,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            start=start,
            end=end,
            limit=limit,
            offset=offset,
        )

    async def count_signals(
        self,
        *,
        strategy_id: uuid.UUID | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        direction: SignalDirection | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        return await self._signals.count_signals(
            strategy_id=strategy_id,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            start=start,
            end=end,
        )
