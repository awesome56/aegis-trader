"""Domain model tests: schema shape, decimals, relationships, defaults."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models import (
    Asset,
    AssetClass,
    Base,
    OrderAction,
    OrderType,
    Portfolio,
    Position,
    PositionSide,
    ProposalStatus,
    Strategy,
    StrategyType,
    TimeHorizon,
    TradeProposal,
    User,
)
from sqlalchemy import select

EXPECTED_TABLES = {
    "users",
    "user_sessions",
    "broker_accounts",
    "portfolios",
    "portfolio_snapshots",
    "assets",
    "watchlists",
    "watchlist_items",
    "positions",
    "market_quotes",
    "market_candles",
    "strategies",
    "strategy_signals",
    "trade_proposals",
    "risk_evaluations",
    "orders",
    "executions",
    "trades",
    "agent_runs",
    "agent_decisions",
    "risk_snapshots",
    "backtests",
    "backtest_results",
    "system_events",
    "notifications",
}


def test_all_expected_tables_registered() -> None:
    assert EXPECTED_TABLES.issubset(set(Base.metadata.tables))


def test_money_columns_use_numeric() -> None:
    from sqlalchemy import Numeric

    column = Base.metadata.tables["portfolios"].c.cash
    assert isinstance(column.type, Numeric)
    assert column.type.asdecimal is True


async def test_model_roundtrip_decimal_and_relationships(db_session) -> None:
    user = User(email=f"model-{uuid.uuid4().hex}@example.com", hashed_password="x")
    asset = Asset(symbol=f"TST{uuid.uuid4().hex[:6].upper()}", asset_class=AssetClass.EQUITY)
    strategy = Strategy(
        name="Test Trend",
        slug=f"trend-{uuid.uuid4().hex[:8]}",
        strategy_type=StrategyType.TREND_FOLLOWING,
    )
    db_session.add_all([user, asset, strategy])
    await db_session.flush()

    portfolio = Portfolio(
        user_id=user.id, name="Main", initial_capital=Decimal("100000"), cash=Decimal("75000.50")
    )
    db_session.add(portfolio)
    await db_session.flush()

    position = Position(
        portfolio_id=portfolio.id,
        asset_id=asset.id,
        symbol=asset.symbol,
        side=PositionSide.LONG,
        quantity=Decimal("10"),
        average_entry_price=Decimal("150.25"),
        market_value=Decimal("1502.50"),
        opened_at=datetime.now(UTC),
    )
    db_session.add(position)

    proposal = TradeProposal(
        portfolio_id=portfolio.id,
        strategy_id=strategy.id,
        symbol=asset.symbol,
        asset_class=AssetClass.EQUITY,
        action=OrderAction.BUY,
        order_type=OrderType.MARKET,
        status=ProposalStatus.PENDING,
        proposed_quantity=Decimal("10"),
        proposed_position_percentage=Decimal("1.5"),
        entry_price=Decimal("150.00"),
        confidence=Decimal("0.78"),
        time_horizon=TimeHorizon.SWING,
        reasoning_summary="Trend remains bullish; momentum improving.",
        expires_at=datetime.now(UTC) + timedelta(hours=4),
    )
    db_session.add(proposal)
    await db_session.flush()

    assert isinstance(portfolio.cash, Decimal)
    assert portfolio.cash == Decimal("75000.50")
    assert position.quantity == Decimal("10")
    assert proposal.confidence == Decimal("0.78")

    fetched = await db_session.execute(select(Portfolio).where(Portfolio.id == portfolio.id))
    loaded = fetched.scalar_one()
    assert loaded.initial_capital == Decimal("100000")
