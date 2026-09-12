import type { ISODateString, Numeric } from './api'

export interface PortfolioSummary {
  portfolio_id: string
  currency: string
  cash: Numeric
  equity: Numeric
  buying_power: Numeric
  invested: Numeric
  market_value: Numeric
  open_pnl: Numeric
  realized_pnl: Numeric
  unrealized_pnl: Numeric
  daily_pnl: Numeric
  total_pnl: Numeric
  total_return_pct: Numeric
  daily_return_pct: Numeric
  exposure_pct: Numeric
  open_positions: number
  updated_at: ISODateString
}

export interface PortfolioSnapshot {
  timestamp: ISODateString
  equity: Numeric
  cash: Numeric
  invested: Numeric
  daily_pnl: Numeric
  total_return_pct: Numeric
  drawdown_pct: Numeric
  benchmark_equity?: Numeric
}

export type PortfolioRange = '1D' | '1W' | '1M' | '3M' | '6M' | 'YTD' | '1Y' | 'ALL'

export interface PortfolioHistory {
  range: PortfolioRange
  currency: string
  points: PortfolioSnapshot[]
}

export interface AllocationSlice {
  label: string
  value: Numeric
  weight_pct: Numeric
}

export interface AllocationBreakdown {
  by_asset: AllocationSlice[]
  by_sector: AllocationSlice[]
  by_asset_class: AllocationSlice[]
}
