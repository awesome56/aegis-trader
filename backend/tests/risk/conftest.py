"""Risk test fixtures and builders."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest_asyncio
from app.brokers.bootstrap import ensure_paper_account
from app.brokers.paper import PaperBrokerAdapter
from app.market.services.cache import InMemoryCacheBackend, MarketDataCache
from app.market.services.freshness import MarketDataFreshnessService
from app.market.services.market_data import MarketDataService
from app.models.enums import TradeSide, TradingState
from app.models.user import User
from app.risk.service import RiskEngine
from app.risk.types import RiskContext, RiskLimitsSnapshot, RiskRequest

from tests.strategies.conftest import FixedMarketProvider, strategy_settings
from tests.strategies.helpers import FIXED_NOW, build_candles, build_quote

NOW = FIXED_NOW


def risk_limits(**overrides: object) -> RiskLimitsSnapshot:
    defaults: dict[str, object] = {
        "is_enabled": True,
        "max_position_percent": Decimal("5"),
        "max_portfolio_exposure_percent": Decimal("80"),
        "max_open_positions": 10,
        "max_daily_loss_percent": Decimal("3"),
        "max_drawdown_percent": Decimal("10"),
        "max_trades_per_day": 20,
        "max_risk_per_trade_percent": Decimal("1"),
        "min_strategy_confidence": Decimal("0.6"),
        "min_reward_risk_ratio": Decimal("2"),
        "require_stop_loss": True,
        "require_strategy_signal": False,
        "max_sector_exposure_percent": Decimal("30"),
        "max_asset_class_exposure_percent": Decimal("60"),
        "unknown_sector_policy": "warn",
        "daily_loss_include_unrealized": True,
        "commission_buffer_bps": Decimal("5"),
    }
    defaults.update(overrides)
    return RiskLimitsSnapshot(**defaults)  # type: ignore[arg-type]


def buy_request(**overrides: object) -> RiskRequest:
    defaults: dict[str, object] = {
        "symbol": "AAPL",
        "side": TradeSide.BUY,
        "requested_quantity": Decimal("10"),
        "entry_price": Decimal("100"),
        "stop_loss": Decimal("95"),
        "take_profit": Decimal("115"),
    }
    defaults.update(overrides)
    return RiskRequest(**defaults)  # type: ignore[arg-type]


def risk_context(**overrides: Any) -> RiskContext:  # noqa: ANN401
    limits = overrides.pop("limits", risk_limits())
    request = overrides.pop("request", buy_request())
    base: dict[str, Any] = {
        "request": request,
        "trading_state": TradingState.TRADING_ENABLED,
        "limits": limits,
        "currency": "USD",
        "equity": Decimal("100000"),
        "cash": Decimal("100000"),
        "buying_power": Decimal("100000"),
        "portfolio_market_value": Decimal("0"),
        "portfolio_exposure_percent": Decimal("0"),
        "symbol_exposure_value": Decimal("0"),
        "symbol_exposure_percent": Decimal("0"),
        "has_existing_position": False,
        "open_positions": 0,
        "sector": "Tech",
        "asset_class": "EQUITY",
        "daily_pnl": Decimal("0"),
        "drawdown_percent": Decimal("0"),
        "trades_today": 0,
        "quote": None,
        "quote_is_stale": False,
        "evaluated_at": NOW,
        "size_caps": {},
    }
    base.update(overrides)
    return RiskContext(**base)


def sample_quote(price: float = 100.0) -> Any:  # noqa: ANN401
    return build_quote(price, timestamp=NOW)


@pytest_asyncio.fixture
async def risk_env(db_session: Any) -> Any:
    async def _build(
        closes: list[float] | None = None,
        *,
        data_now: datetime = FIXED_NOW,
        clock_now: datetime | None = None,
        **settings_overrides: object,
    ) -> SimpleNamespace:
        settings = strategy_settings(**settings_overrides)
        effective_clock = clock_now or data_now
        candles = build_candles(closes or [100.0 + 0.5 * i for i in range(80)], end=data_now)
        provider = FixedMarketProvider(candles, now=data_now)
        cache = MarketDataCache(backend=InMemoryCacheBackend(), settings=settings)
        freshness = MarketDataFreshnessService(settings, clock=lambda: effective_clock)
        market = MarketDataService(
            db_session, provider=provider, cache=cache, freshness=freshness, settings=settings
        )
        user = User(
            email=f"risk-{uuid.uuid4().hex[:10]}@example.com", hashed_password="x", is_active=True
        )
        db_session.add(user)
        await db_session.flush()
        account, portfolio = await ensure_paper_account(db_session, user, settings)
        engine = RiskEngine(
            db_session, market, user, settings=settings, clock=lambda: effective_clock
        )
        broker = PaperBrokerAdapter(db_session, account, portfolio, market, settings=settings)
        return SimpleNamespace(
            settings=settings,
            market=market,
            user=user,
            account=account,
            portfolio=portfolio,
            engine=engine,
            broker=broker,
            session=db_session,
            now=effective_clock,
        )

    return _build
