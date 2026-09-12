"""PortfolioService: valuation, allocation, snapshots, history, drawdown."""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from app.brokers.types import BrokerOrderRequest
from app.models.enums import TradeSide
from app.models.portfolio import PortfolioSnapshot
from app.repositories.portfolio import PortfolioSnapshotRepository
from sqlalchemy import func, select

from tests.brokers.conftest import FIXED_NOW


async def _buy(env, symbol: str = "AAPL", qty: str = "10", key: str = "k") -> None:  # noqa: ANN001
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol=symbol, side=TradeSide.BUY, quantity=Decimal(qty), idempotency_key=key
        )
    )


async def test_empty_portfolio_summary(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env()
    summary = await env.service.summary()
    assert summary.equity == Decimal("100000.0000000000")
    assert summary.cash == Decimal("100000.0000000000")
    assert summary.market_value == Decimal("0")
    assert summary.invested_amount == Decimal("0")
    assert summary.unrealized_pnl == Decimal("0")
    assert summary.total_pnl == Decimal("0")
    assert summary.total_return_percent == Decimal("0")
    assert summary.exposure_percent == Decimal("0")
    assert summary.position_count == 0
    assert summary.daily_pnl is None
    assert summary.daily_return_percent is None


async def test_summary_after_buy(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env()
    await _buy(env, qty="10")
    summary = await env.service.summary()
    assert summary.position_count == 1
    assert summary.market_value > 0
    assert summary.invested_amount > 0
    assert summary.cash < Decimal("100000")
    # equity = cash + market value (marked at bid)
    assert summary.equity == summary.cash + summary.market_value
    assert summary.exposure_percent == (
        summary.market_value / summary.equity * Decimal("100")
    ).quantize(Decimal("0.0000000001"))


async def test_positions_include_weight_and_asset_metadata(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env()
    await _buy(env, qty="10")
    positions = await env.service.positions()
    assert len(positions) == 1
    position = positions[0]
    assert position.symbol == "AAPL"
    assert position.asset_name is not None
    assert position.asset_class == "EQUITY"
    assert Decimal("0") < position.weight_percent < Decimal("100")
    assert position.price_stale is False


async def test_allocation_breakdown(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env()
    await _buy(env, qty="10")
    allocation = await env.service.allocation()
    labels = {slice_.label for slice_ in allocation.by_symbol}
    assert "AAPL" in labels and "CASH" in labels
    class_labels = {slice_.label for slice_ in allocation.by_asset_class}
    assert "EQUITY" in class_labels and "CASH" in class_labels
    # sector metadata is absent for the mock asset -> UNKNOWN bucket
    sector_labels = {slice_.label for slice_ in allocation.by_sector}
    assert "UNKNOWN" in sector_labels
    total_weight = sum((slice_.weight_percent for slice_ in allocation.by_symbol), Decimal("0"))
    assert abs(total_weight - Decimal("100")) < Decimal("0.01")


async def test_snapshot_creation_and_dedupe(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env()
    await _buy(env, qty="5")
    first = await env.service.create_snapshot()
    second = await env.service.create_snapshot()
    assert first.id == second.id
    count = await env.session.scalar(
        select(func.count())
        .select_from(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == env.portfolio.id)
    )
    assert count == 1
    assert first.position_count == 1
    assert first.market_value > 0


async def test_daily_pnl_from_previous_snapshot(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env()
    # Snapshot recorded yesterday at the pre-trade equity.
    snapshots = PortfolioSnapshotRepository(env.session)
    baseline = PortfolioSnapshot(
        portfolio_id=env.portfolio.id,
        snapshot_time=FIXED_NOW - timedelta(days=1),
        cash=Decimal("100000"),
        equity=Decimal("100000"),
        buying_power=Decimal("100000"),
        invested=Decimal("0"),
        market_value=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"),
        daily_pnl=Decimal("0"),
        total_return_pct=Decimal("0"),
        daily_return_pct=Decimal("0"),
        exposure_pct=Decimal("0"),
        position_count=0,
    )
    await snapshots.add(baseline)
    await _buy(env, qty="10")

    summary = await env.service.summary()
    assert summary.daily_pnl is not None
    assert summary.daily_pnl == summary.equity - Decimal("100000")
    assert summary.daily_return_percent is not None


async def test_history_ranges_and_custom(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env()
    snapshots = PortfolioSnapshotRepository(env.session)
    for days in (40, 20, 5, 1):
        await snapshots.add(
            PortfolioSnapshot(
                portfolio_id=env.portfolio.id,
                snapshot_time=FIXED_NOW - timedelta(days=days),
                cash=Decimal("100000"),
                equity=Decimal(str(100000 + days * 10)),
                buying_power=Decimal("100000"),
                invested=Decimal("0"),
                market_value=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                daily_pnl=Decimal("0"),
                total_return_pct=Decimal("0"),
                daily_return_pct=Decimal("0"),
                exposure_pct=Decimal("0"),
                position_count=0,
            )
        )

    week = await env.service.history("1W")
    assert week.range == "1W"
    assert week.point_count == 2  # 1 and 5 day-old snapshots
    month = await env.service.history("1M")
    assert month.point_count == 3  # 1, 5, 20 days
    all_points = await env.service.history("ALL")
    assert all_points.point_count == 4
    ytd = await env.service.history("YTD")
    assert ytd.start is not None and ytd.start.month == 1


async def test_history_rejects_unknown_range(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env()
    with pytest.raises(ValueError):
        await env.service.history("2Y")


async def test_history_downsampling(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env(PORTFOLIO_HISTORY_MAX_POINTS=3)
    snapshots = PortfolioSnapshotRepository(env.session)
    for index in range(20):
        await snapshots.add(
            PortfolioSnapshot(
                portfolio_id=env.portfolio.id,
                snapshot_time=FIXED_NOW - timedelta(days=index + 1),
                cash=Decimal("100000"),
                equity=Decimal(str(100000 + index)),
                buying_power=Decimal("100000"),
                invested=Decimal("0"),
                market_value=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                daily_pnl=Decimal("0"),
                total_return_pct=Decimal("0"),
                daily_return_pct=Decimal("0"),
                exposure_pct=Decimal("0"),
                position_count=0,
            )
        )
    history = await env.service.history("ALL")
    assert history.downsampled is True
    assert history.point_count <= 4


async def test_current_drawdown(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env()
    snapshots = PortfolioSnapshotRepository(env.session)
    await snapshots.add(
        PortfolioSnapshot(
            portfolio_id=env.portfolio.id,
            snapshot_time=FIXED_NOW - timedelta(days=3),
            cash=Decimal("200000"),
            equity=Decimal("200000"),
            buying_power=Decimal("200000"),
            invested=Decimal("0"),
            market_value=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            daily_pnl=Decimal("0"),
            total_return_pct=Decimal("0"),
            daily_return_pct=Decimal("0"),
            exposure_pct=Decimal("0"),
            position_count=0,
        )
    )
    drawdown = await env.service.drawdown_percent()
    assert drawdown == Decimal("-50.0000000000")


async def test_position_detail_lookup(portfolio_env) -> None:  # noqa: ANN001
    env = await portfolio_env()
    await _buy(env, qty="3")
    positions = await env.service.positions()
    fetched = await env.service.get_position(positions[0].id)
    assert fetched is not None and fetched.symbol == "AAPL"
    assert await env.service.get_position(uuid.uuid4()) is None
