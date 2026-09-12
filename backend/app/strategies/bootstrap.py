"""Idempotent strategy bootstrap.

Strategies are identified by a stable ``slug`` key, never by display name.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.enums import StrategyType
from app.models.strategy import Strategy
from app.repositories.strategy import StrategyRepository
from app.strategies.enums import StrategyKey

ASSET_CLASSES = ["EQUITY", "ETF"]


def _configuration_summary(settings: Settings, key: StrategyKey) -> dict[str, float | int | bool]:
    if key is StrategyKey.TREND_FOLLOWING:
        return {
            "fast_period": settings.STRATEGY_TREND_FAST_PERIOD,
            "slow_period": settings.STRATEGY_TREND_SLOW_PERIOD,
            "atr_period": settings.STRATEGY_TREND_ATR_PERIOD,
            "slope_lookback": settings.STRATEGY_TREND_SLOPE_LOOKBACK,
            "min_ma_spread_bps": settings.STRATEGY_TREND_MIN_MA_SPREAD_BPS,
            "min_confidence": settings.STRATEGY_TREND_MIN_CONFIDENCE,
            "allow_high_volatility": settings.STRATEGY_TREND_ALLOW_HIGH_VOLATILITY,
        }
    if key is StrategyKey.MOMENTUM:
        return {
            "rsi_period": settings.STRATEGY_MOMENTUM_RSI_PERIOD,
            "macd_fast": settings.STRATEGY_MOMENTUM_MACD_FAST_PERIOD,
            "macd_slow": settings.STRATEGY_MOMENTUM_MACD_SLOW_PERIOD,
            "macd_signal": settings.STRATEGY_MOMENTUM_MACD_SIGNAL_PERIOD,
            "min_relative_volume": settings.STRATEGY_MOMENTUM_MIN_RELATIVE_VOLUME,
            "min_confidence": settings.STRATEGY_MOMENTUM_MIN_CONFIDENCE,
            "allow_high_volatility": settings.STRATEGY_MOMENTUM_ALLOW_HIGH_VOLATILITY,
        }
    return {
        "bollinger_period": settings.STRATEGY_MEAN_REVERSION_BOLLINGER_PERIOD,
        "bollinger_stddev": settings.STRATEGY_MEAN_REVERSION_BOLLINGER_STDDEV,
        "percent_b_low": settings.STRATEGY_MEAN_REVERSION_PERCENT_B_LOW,
        "percent_b_high": settings.STRATEGY_MEAN_REVERSION_PERCENT_B_HIGH,
        "require_confirmation": settings.STRATEGY_MEAN_REVERSION_REQUIRE_CONFIRMATION,
        "allow_trending": settings.STRATEGY_MEAN_REVERSION_ALLOW_TRENDING,
        "min_confidence": settings.STRATEGY_MEAN_REVERSION_MIN_CONFIDENCE,
    }


def strategy_definitions(
    settings: Settings | None = None,
) -> list[dict[str, object]]:
    settings = settings or get_settings()
    return [
        {
            "slug": StrategyKey.TREND_FOLLOWING.value,
            "name": "Trend Following",
            "strategy_type": StrategyType.TREND_FOLLOWING,
            "priority": 10,
            "description": (
                "Rides sustained directional moves using EMA fast/slow structure, "
                "slow-EMA slope and ATR-confirmed separation."
            ),
        },
        {
            "slug": StrategyKey.MOMENTUM.value,
            "name": "Momentum",
            "strategy_type": StrategyType.MOMENTUM,
            "priority": 20,
            "description": (
                "Continuation signals from MACD, a positive-but-not-overbought RSI "
                "band and relative-volume confirmation."
            ),
        },
        {
            "slug": StrategyKey.MEAN_REVERSION.value,
            "name": "Mean Reversion",
            "strategy_type": StrategyType.MEAN_REVERSION,
            "priority": 30,
            "description": (
                "Fades stretches beyond the Bollinger Bands, confirmed by RSI "
                "extremes, in non-trending, non-extreme-volatility regimes."
            ),
        },
    ]


async def ensure_strategies(
    session: AsyncSession, settings: Settings | None = None
) -> list[Strategy]:
    """Create any missing strategy rows. Returns the created rows only."""
    settings = settings or get_settings()
    repository = StrategyRepository(session)
    created: list[Strategy] = []
    for definition in strategy_definitions(settings):
        slug = str(definition["slug"])
        if await repository.get_by_slug(slug) is not None:
            continue
        strategy = Strategy(
            slug=slug,
            name=str(definition["name"]),
            strategy_type=cast(StrategyType, definition["strategy_type"]),
            description=str(definition["description"]),
            is_enabled=False,
            timeframe=settings.STRATEGY_DEFAULT_TIMEFRAME,
            priority=cast(int, definition["priority"]),
            parameters=_configuration_summary(settings, StrategyKey(slug)),
            asset_classes=ASSET_CLASSES,
        )
        created.append(await repository.add(strategy))
    return created
