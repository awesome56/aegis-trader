"""Market-data freshness / staleness service.

Freshness is always measured against the **market timestamp** supplied by the
provider — never the time the backend received the data. Later phases (Order
Manager) call :meth:`assert_quote_fresh` to fail closed before execution.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.core.config import Settings, get_settings
from app.market.domain.models import Candle, FreshnessAssessment, MarketQuote
from app.market.enums import Timeframe
from app.market.exceptions import StaleMarketDataError


class MarketDataFreshnessService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._clock = clock or (lambda: datetime.now(UTC))

    def _now(self) -> datetime:
        return self._clock().astimezone(UTC)

    def max_candle_age_seconds(self, timeframe: Timeframe) -> int:
        if timeframe.is_intraday:
            return self._settings.MAX_INTRADAY_CANDLE_AGE_SECONDS
        return self._settings.MAX_DAILY_CANDLE_AGE_SECONDS

    def _age(self, timestamp: datetime) -> float:
        return max(0.0, (self._now() - timestamp.astimezone(UTC)).total_seconds())

    def assess_quote(self, quote: MarketQuote) -> FreshnessAssessment:
        return self._assess(
            "quote", quote.symbol, quote.market_timestamp, self._settings.MAX_QUOTE_AGE_SECONDS
        )

    def assess_candle(self, candle: Candle) -> FreshnessAssessment:
        return self._assess(
            "candle",
            candle.symbol,
            candle.close_time or candle.open_time,
            self.max_candle_age_seconds(candle.timeframe),
        )

    def _assess(
        self, kind: str, symbol: str, timestamp: datetime, max_age_seconds: int
    ) -> FreshnessAssessment:
        age = self._age(timestamp)
        return FreshnessAssessment(  # type: ignore[arg-type]
            kind=kind,
            symbol=symbol,
            market_timestamp=timestamp,
            age_seconds=age,
            max_age_seconds=max_age_seconds,
            is_stale=age > max_age_seconds,
        )

    def is_quote_fresh(self, quote: MarketQuote) -> bool:
        return not self.assess_quote(quote).is_stale

    def is_candle_fresh(self, candle: Candle) -> bool:
        return not self.assess_candle(candle).is_stale

    def assert_quote_fresh(self, quote: MarketQuote) -> MarketQuote:
        assessment = self.assess_quote(quote)
        if assessment.is_stale:
            raise StaleMarketDataError(
                f"Quote for {quote.symbol} is stale ({assessment.age_seconds:.1f}s old, "
                f"max {assessment.max_age_seconds}s)",
                details={
                    "symbol": quote.symbol,
                    "age_seconds": round(assessment.age_seconds, 3),
                    "max_age_seconds": assessment.max_age_seconds,
                    "market_timestamp": quote.market_timestamp.isoformat(),
                    "provider": quote.provider,
                },
            )
        return quote

    def assert_candle_fresh(self, candle: Candle) -> Candle:
        assessment = self.assess_candle(candle)
        if assessment.is_stale:
            raise StaleMarketDataError(
                f"Latest {candle.timeframe.value} candle for {candle.symbol} is stale "
                f"({assessment.age_seconds:.1f}s old, max {assessment.max_age_seconds}s)",
                details={
                    "symbol": candle.symbol,
                    "timeframe": candle.timeframe.value,
                    "age_seconds": round(assessment.age_seconds, 3),
                    "max_age_seconds": assessment.max_age_seconds,
                    "market_timestamp": assessment.market_timestamp.isoformat(),
                    "provider": candle.provider,
                },
            )
        return candle
