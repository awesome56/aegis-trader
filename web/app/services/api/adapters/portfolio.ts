import type { PortfolioHistory, PortfolioSnapshot, PortfolioRange, PortfolioSummary } from '~/types/portfolio'
import { iso, num } from './common'
import type { RawPortfolioHistory, RawPortfolioSummary, RawSnapshotPoint } from './raw'

export function toPortfolioSummary(raw: RawPortfolioSummary): PortfolioSummary {
  return {
    portfolio_id: raw.portfolio_id,
    currency: raw.currency,
    cash: num(raw.cash),
    equity: num(raw.equity),
    buying_power: num(raw.buying_power),
    invested: num(raw.invested_amount),
    market_value: num(raw.market_value),
    open_pnl: num(raw.unrealized_pnl),
    realized_pnl: num(raw.realized_pnl),
    unrealized_pnl: num(raw.unrealized_pnl),
    daily_pnl: num(raw.daily_pnl),
    total_pnl: num(raw.total_pnl),
    total_return_pct: num(raw.total_return_percent),
    daily_return_pct: num(raw.daily_return_percent),
    exposure_pct: num(raw.exposure_percent),
    open_positions: raw.position_count,
    updated_at: iso(raw.updated_at),
  }
}

export function toSnapshotPoint(raw: RawSnapshotPoint): PortfolioSnapshot {
  return {
    timestamp: iso(raw.snapshot_time),
    equity: num(raw.equity),
    cash: num(raw.cash),
    invested: num(raw.market_value),
    daily_pnl: num(raw.daily_pnl),
    total_return_pct: num(raw.total_return_percent),
    drawdown_pct: 0,
  }
}

export function toPortfolioHistory(raw: RawPortfolioHistory): PortfolioHistory {
  return {
    range: raw.range as PortfolioRange,
    currency: 'USD',
    points: raw.points.map(toSnapshotPoint),
  }
}
