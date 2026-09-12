"""Portfolio aggregation, valuation, snapshots and history.

PortfolioService sits **above** the broker: it never executes orders. It values
the broker account's persisted state and produces the read models the web and
mobile clients consume. Broker-side accounting (cash, cost basis, realized P&L)
remains the single source of truth; this service only aggregates it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.accounting import market_value, percent_of, q, return_percent, unrealized_pnl
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.market.domain.models import MarketQuote
from app.market.services.market_data import MarketDataService
from app.models.broker import BrokerAccount
from app.models.portfolio import Portfolio, PortfolioSnapshot
from app.models.position import Position
from app.portfolio.types import (
    AllocationBreakdown,
    AllocationSlice,
    PortfolioHistory,
    PortfolioSummary,
    PositionValuation,
    SnapshotPoint,
)
from app.repositories.asset import AssetRepository
from app.repositories.portfolio import PortfolioSnapshotRepository
from app.repositories.position import PositionRepository

logger = get_logger(__name__)

_RANGE_DAYS: dict[str, int | None] = {
    "1D": 1,
    "1W": 7,
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "ALL": None,
}
SUPPORTED_RANGES = ("1D", "1W", "1M", "3M", "6M", "YTD", "1Y", "ALL")
UNKNOWN_LABEL = "UNKNOWN"
CASH_LABEL = "CASH"


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; Postgres returns tz-aware. Normalise."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class _MarkedPosition(NamedTuple):
    position: Position
    mark: Decimal
    market_value: Decimal
    unrealized: Decimal
    price_timestamp: datetime | None
    price_stale: bool


class _Valuation(NamedTuple):
    cash: Decimal
    buying_power: Decimal
    realized_pnl: Decimal
    market_value: Decimal
    invested_amount: Decimal
    unrealized_pnl: Decimal
    equity: Decimal
    currency: str
    positions: list[_MarkedPosition]
    updated_at: datetime | None


class PortfolioService:
    def __init__(
        self,
        session: AsyncSession,
        portfolio: Portfolio,
        market: MarketDataService,
        *,
        account: BrokerAccount | None = None,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._portfolio = portfolio
        self._account = account
        self._market = market
        self._settings = settings or get_settings()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._positions = PositionRepository(session)
        self._assets = AssetRepository(session)
        self._snapshots = PortfolioSnapshotRepository(session)

    # --- valuation ----------------------------------------------------------
    async def _quote_map(self, symbols: Iterable[str]) -> dict[str, MarketQuote | None]:
        quotes: dict[str, MarketQuote | None] = {}
        for symbol in symbols:
            if symbol in quotes:
                continue
            try:
                quotes[symbol] = await self._market.get_quote(symbol)
            except Exception as exc:  # noqa: BLE001 - valuation must not fail reads
                logger.warning("portfolio_quote_unavailable", symbol=symbol, error=str(exc))
                quotes[symbol] = None
        return quotes

    async def _value(self) -> _Valuation:
        positions = await self._positions.list_open(self._portfolio.id)
        quotes = await self._quote_map(position.symbol for position in positions)

        marked: list[_MarkedPosition] = []
        total_market_value = Decimal("0")
        total_invested = Decimal("0")
        total_unrealized = Decimal("0")
        updated_at: datetime | None = self._portfolio.updated_at

        for position in positions:
            quote = quotes.get(position.symbol)
            stale = True
            price_timestamp: datetime | None = None
            if quote is not None:
                mark = quote.bid if quote.bid is not None else quote.last
                assessment = self._market.freshness.assess_quote(quote)
                stale = assessment.is_stale
                price_timestamp = quote.market_timestamp
            else:
                mark = position.current_price or position.average_entry_price
            value = market_value(position.quantity, mark)
            unrealized = unrealized_pnl(position.quantity, position.average_entry_price, mark)
            marked.append(
                _MarkedPosition(position, mark, value, unrealized, price_timestamp, stale)
            )
            total_market_value += value
            total_invested += Decimal(str(position.cost_basis))
            total_unrealized += unrealized
            if position.updated_at and (updated_at is None or position.updated_at > updated_at):
                updated_at = position.updated_at

        cash = Decimal(str(self._account.cash_balance if self._account else self._portfolio.cash))
        buying_power = Decimal(
            str(self._account.buying_power if self._account else self._portfolio.cash)
        )
        realized = (
            Decimal(str(self._account.realized_pnl))
            if self._account is not None
            else sum((Decimal(str(p.realized_pnl)) for p in positions), Decimal("0"))
        )
        equity = q(cash + total_market_value)
        return _Valuation(
            cash=q(cash),
            buying_power=q(buying_power),
            realized_pnl=q(realized),
            market_value=q(total_market_value),
            invested_amount=q(total_invested),
            unrealized_pnl=q(total_unrealized),
            equity=equity,
            currency=self._portfolio.base_currency,
            positions=marked,
            updated_at=updated_at,
        )

    async def _daily_pnl(self, equity: Decimal) -> tuple[Decimal | None, Decimal | None]:
        now = self._clock()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        previous = await self._snapshots.latest_before(self._portfolio.id, midnight)
        if previous is None:
            return None, None
        baseline = Decimal(str(previous.equity))
        if baseline == 0:
            return None, None
        daily = q(equity - baseline)
        return daily, percent_of(daily, baseline)

    async def _drawdown(self, equity: Decimal) -> Decimal:
        peak = await self._snapshots.peak_equity(self._portfolio.id)
        peak_value = Decimal(str(peak)) if peak is not None else equity
        if peak_value <= 0 or equity >= peak_value:
            return Decimal("0")
        return q((equity - peak_value) / peak_value * Decimal("100"))

    # --- summary ------------------------------------------------------------
    async def summary(self) -> PortfolioSummary:
        valuation = await self._value()
        daily_pnl, daily_return = await self._daily_pnl(valuation.equity)
        initial = Decimal(str(self._portfolio.initial_capital))
        total_return = percent_of(valuation.equity - initial, initial) if initial else Decimal("0")
        exposure = percent_of(valuation.market_value, valuation.equity)
        return PortfolioSummary(
            portfolio_id=self._portfolio.id,
            currency=valuation.currency,
            equity=valuation.equity,
            cash=valuation.cash,
            buying_power=valuation.buying_power,
            invested_amount=valuation.invested_amount,
            market_value=valuation.market_value,
            realized_pnl=valuation.realized_pnl,
            unrealized_pnl=valuation.unrealized_pnl,
            total_pnl=q(valuation.realized_pnl + valuation.unrealized_pnl),
            daily_pnl=daily_pnl,
            daily_return_percent=daily_return,
            total_return_percent=total_return,
            exposure_percent=exposure,
            position_count=len(valuation.positions),
            initial_capital=initial,
            updated_at=valuation.updated_at,
        )

    # --- positions ----------------------------------------------------------
    async def positions(self) -> list[PositionValuation]:
        valuation = await self._value()
        asset_ids = [m.position.asset_id for m in valuation.positions if m.position.asset_id]
        assets = await self._assets.list_by_ids(asset_ids)

        results: list[PositionValuation] = []
        for marked in valuation.positions:
            position = marked.position
            asset = assets.get(position.asset_id) if position.asset_id else None
            results.append(
                PositionValuation(
                    id=position.id,
                    symbol=position.symbol,
                    asset_name=asset.name if asset else None,
                    asset_class=asset.asset_class.value if asset else None,
                    sector=asset.sector if asset else None,
                    quantity=Decimal(str(position.quantity)),
                    average_entry_price=Decimal(str(position.average_entry_price)),
                    current_price=marked.mark,
                    market_value=marked.market_value,
                    cost_basis=Decimal(str(position.cost_basis)),
                    weight_percent=percent_of(marked.market_value, valuation.equity),
                    unrealized_pnl=marked.unrealized,
                    unrealized_return_percent=return_percent(
                        marked.unrealized, Decimal(str(position.cost_basis))
                    ),
                    realized_pnl=Decimal(str(position.realized_pnl)),
                    opened_at=position.opened_at,
                    updated_at=position.updated_at,
                    price_timestamp=marked.price_timestamp,
                    price_stale=marked.price_stale,
                )
            )
        return results

    async def get_position(self, position_id) -> PositionValuation | None:  # noqa: ANN001
        for position in await self.positions():
            if position.id == position_id:
                return position
        return None

    async def drawdown_percent(self) -> Decimal:
        """Current drawdown from the historical peak equity (0 or negative %)."""
        return await self._drawdown((await self._value()).equity)

    # --- allocation ---------------------------------------------------------
    async def allocation(self) -> AllocationBreakdown:
        valuation = await self._value()
        asset_ids = [m.position.asset_id for m in valuation.positions if m.position.asset_id]
        assets = await self._assets.list_by_ids(asset_ids)

        by_symbol: list[AllocationSlice] = []
        class_totals: dict[str, Decimal] = {}
        sector_totals: dict[str, Decimal] = {}
        for marked in valuation.positions:
            position = marked.position
            by_symbol.append(
                AllocationSlice(
                    label=position.symbol,
                    value=marked.market_value,
                    weight_percent=percent_of(marked.market_value, valuation.equity),
                )
            )
            asset = assets.get(position.asset_id) if position.asset_id else None
            class_label = asset.asset_class.value if asset else UNKNOWN_LABEL
            sector_label = asset.sector if asset and asset.sector else UNKNOWN_LABEL
            class_totals[class_label] = (
                class_totals.get(class_label, Decimal("0")) + marked.market_value
            )
            sector_totals[sector_label] = (
                sector_totals.get(sector_label, Decimal("0")) + marked.market_value
            )

        if valuation.cash > 0:
            by_symbol.append(
                AllocationSlice(
                    label=CASH_LABEL,
                    value=valuation.cash,
                    weight_percent=percent_of(valuation.cash, valuation.equity),
                )
            )
            class_totals[CASH_LABEL] = class_totals.get(CASH_LABEL, Decimal("0")) + valuation.cash
            sector_totals[CASH_LABEL] = sector_totals.get(CASH_LABEL, Decimal("0")) + valuation.cash

        return AllocationBreakdown(
            total_equity=valuation.equity,
            cash_weight_percent=percent_of(valuation.cash, valuation.equity),
            by_symbol=by_symbol,
            by_asset_class=_slices(class_totals, valuation.equity),
            by_sector=_slices(sector_totals, valuation.equity),
        )

    # --- snapshots ----------------------------------------------------------
    async def create_snapshot(self, *, at: datetime | None = None) -> PortfolioSnapshot:
        """Create an interval-bucketed snapshot. Duplicate buckets are skipped."""
        interval = max(1, self._settings.PORTFOLIO_SNAPSHOT_INTERVAL_SECONDS)
        now = at or self._clock()
        bucket = datetime.fromtimestamp(int(now.timestamp()) // interval * interval, tz=UTC)

        latest = await self._snapshots.latest(self._portfolio.id)
        if latest is not None:
            latest_time = _as_utc(latest.snapshot_time)
            if latest_time >= bucket:
                latest.snapshot_time = latest_time
                return latest

        valuation = await self._value()
        daily_pnl, daily_return = await self._daily_pnl(valuation.equity)
        initial = Decimal(str(self._portfolio.initial_capital))
        total_return = percent_of(valuation.equity - initial, initial) if initial else Decimal("0")
        exposure = percent_of(valuation.market_value, valuation.equity)

        snapshot = PortfolioSnapshot(
            portfolio_id=self._portfolio.id,
            snapshot_time=bucket,
            cash=valuation.cash,
            equity=valuation.equity,
            buying_power=valuation.buying_power,
            invested=valuation.invested_amount,
            market_value=valuation.market_value,
            unrealized_pnl=valuation.unrealized_pnl,
            realized_pnl=valuation.realized_pnl,
            daily_pnl=daily_pnl or Decimal("0"),
            total_return_pct=total_return,
            daily_return_pct=daily_return or Decimal("0"),
            exposure_pct=exposure,
            position_count=len(valuation.positions),
            positions=[
                {
                    "symbol": marked.position.symbol,
                    "quantity": str(marked.position.quantity),
                    "mark": str(marked.mark),
                    "market_value": str(marked.market_value),
                }
                for marked in valuation.positions
            ],
        )
        self._session.add(snapshot)
        await self._session.flush()
        return snapshot

    async def history(
        self, range_key: str = "1M", *, start: datetime | None = None, end: datetime | None = None
    ) -> PortfolioHistory:
        key = range_key.upper()
        if key not in SUPPORTED_RANGES:
            raise ValueError(f"Unsupported range {range_key!r}")
        now = self._clock()
        window_start = start
        if window_start is None:
            if key == "YTD":
                window_start = now.replace(
                    month=1, day=1, hour=0, minute=0, second=0, microsecond=0
                )
            else:
                days = _RANGE_DAYS[key]
                window_start = now - timedelta(days=days) if days is not None else None

        rows = await self._snapshots.list_range(self._portfolio.id, window_start, end)
        max_points = max(2, self._settings.PORTFOLIO_HISTORY_MAX_POINTS)
        downsampled = len(rows) > max_points
        if downsampled:
            step = (len(rows) + max_points - 1) // max_points
            selected = rows[::step]
            if rows and selected[-1] is not rows[-1]:
                selected.append(rows[-1])
        else:
            selected = rows

        equity = (await self._value()).equity
        points = [
            SnapshotPoint(
                snapshot_time=_as_utc(row.snapshot_time),
                equity=Decimal(str(row.equity)),
                cash=Decimal(str(row.cash)),
                market_value=Decimal(str(row.market_value)),
                realized_pnl=Decimal(str(row.realized_pnl)),
                unrealized_pnl=Decimal(str(row.unrealized_pnl)),
                total_return_percent=Decimal(str(row.total_return_pct)),
                daily_pnl=Decimal(str(row.daily_pnl)),
                exposure_percent=Decimal(str(row.exposure_pct)),
                position_count=row.position_count,
            )
            for row in selected
        ]
        return PortfolioHistory(
            range=key,
            start=window_start,
            end=end,
            point_count=len(points),
            downsampled=downsampled,
            drawdown_percent=await self._drawdown(equity),
            points=points,
        )


def _slices(totals: dict[str, Decimal], equity: Decimal) -> list[AllocationSlice]:
    return [
        AllocationSlice(label=label, value=q(value), weight_percent=percent_of(value, equity))
        for label, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]
