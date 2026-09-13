"""Seed deterministic strategy signals for development and validation.

This runs the **real** strategy engine (``StrategyService`` → ``MarketRegimeService``
→ Phase 2 indicators) against deterministic mock-market scenarios and persists
the resulting ``StrategySignal`` rows. It does not insert signals directly, does
not create TradeProposals, and never touches orders, positions, cash or risk
state.

Usage (development only):

    # default: uses the configured universe and STRATEGY_DEFAULT_TIMEFRAME
    python -m scripts.seed_strategy_signals

    # force a scenario and a couple of symbols
    MOCK_MARKET_SCENARIO=uptrend python -m scripts.seed_strategy_signals --symbols AAPL,MSFT

    # run a specific scenario without changing the environment
    python -m scripts.seed_strategy_signals --scenario mean_reversion_oversold

Running twice within the same candle window is safe: signal persistence is
de-duplicated by (strategy, symbol, timeframe, direction, data_timestamp).
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence

from app.core.config import Settings, get_settings
from app.database.session import dispose_engine, get_session_factory
from app.market.providers.factory import get_market_data_provider, reset_market_data_provider
from app.market.providers.scenarios import SCENARIOS
from app.market.services.market_data import MarketDataService
from app.repositories.strategy import StrategyRepository, StrategySignalRepository
from app.strategies.bootstrap import ensure_strategies
from app.strategies.service import StrategyService
from sqlalchemy.ext.asyncio import AsyncSession

# Disable provider caching so a scenario change is reflected immediately.
_CACHE_OVERRIDES = {
    "MARKET_CANDLE_CACHE_TTL_SECONDS": 0,
    "MARKET_QUOTE_CACHE_TTL_SECONDS": 0,
    "STRATEGY_ANALYSIS_MAX_AGE_MULTIPLIER": 1_000_000.0,
}


def build_settings(scenario: str | None) -> Settings:
    settings = get_settings()
    overrides: dict[str, object] = dict(_CACHE_OVERRIDES)
    if scenario:
        overrides["MOCK_MARKET_SCENARIO"] = scenario
    return settings.model_copy(update=overrides)


async def seed(
    session: AsyncSession,
    settings: Settings,
    *,
    symbols: Sequence[str],
    timeframe: str,
    enable: bool = True,
    persist: bool = True,
) -> dict[str, list]:
    """Evaluate strategies and persist signals. Returns results per symbol."""
    await ensure_strategies(session, settings)
    if enable:
        for strategy in await StrategyRepository(session).list_all():
            strategy.is_enabled = True
        await session.flush()

    reset_market_data_provider()
    try:
        market = MarketDataService(
            session, provider=get_market_data_provider(settings), settings=settings
        )
        service = StrategyService(session, market, settings=settings)
        results: dict[str, list] = {}
        for symbol in symbols:
            results[symbol] = await service.evaluate(symbol, timeframe, persist=persist)
    finally:
        # Never leave a scenario-configured provider memoised globally.
        reset_market_data_provider()
    return results


async def main(args: argparse.Namespace) -> None:
    settings = build_settings(args.scenario)
    symbols = (
        [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        if args.symbols
        else settings.worker_strategy_symbols
    )
    timeframe = args.timeframe or settings.STRATEGY_DEFAULT_TIMEFRAME

    factory = get_session_factory()
    async with factory() as session:
        results = await seed(
            session,
            settings,
            symbols=symbols,
            timeframe=timeframe,
            enable=not args.no_enable,
            persist=not args.dry_run,
        )
        await session.commit()
        total = await StrategySignalRepository(session).count_signals()

    reset_market_data_provider()
    await dispose_engine()

    print(f"scenario={settings.MOCK_MARKET_SCENARIO or 'default'} timeframe={timeframe}")
    for symbol, per_symbol in results.items():
        for result in per_symbol:
            if result.signal is not None:
                print(
                    f"  {symbol:6s} {result.strategy_key:16s} SIGNAL "
                    f"{result.signal.direction.value:5s} "
                    f"confidence={result.signal.confidence} "
                    f"strength={result.signal.strength}"
                )
            else:
                print(
                    f"  {symbol:6s} {result.strategy_key:16s} "
                    f"{result.status.value}: {result.reason}"
                )
    print(f"persisted strategy signals (all): {total}")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default=None)
    parser.add_argument(
        "--symbols", default="", help="comma-separated; default = configured universe"
    )
    parser.add_argument("--timeframe", default="", help="default = STRATEGY_DEFAULT_TIMEFRAME")
    parser.add_argument("--no-enable", action="store_true", help="do not enable strategies first")
    parser.add_argument("--dry-run", action="store_true", help="evaluate without persisting")
    return parser.parse_args(argv)


if __name__ == "__main__":
    asyncio.run(main(_parse_args()))
