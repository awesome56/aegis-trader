/** Frontend backtest domain types (aligned to the live backend contract). */

import type { ISODateString, Numeric } from './api'

export type BacktestStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

export interface BacktestConfig {
  strategy_id: string
  name?: string
  symbols: string[]
  timeframe: string
  start_date: ISODateString
  end_date: ISODateString
  initial_capital: Numeric
  position_size_percent?: Numeric
  fees_pct?: Numeric
  slippage_pct?: Numeric
  benchmark_symbol?: string
  force_close_at_end?: boolean
}

export interface Backtest {
  id: string
  name: string
  strategy_id: string | null
  strategy_name: string | null
  symbols: string[]
  timeframe: string
  start_date: ISODateString
  end_date: ISODateString
  initial_capital: Numeric
  benchmark_symbol: string | null
  status: BacktestStatus
  created_at: ISODateString
  started_at: ISODateString | null
  completed_at: ISODateString | null
  error: string | null
  final_capital: Numeric | null
  total_return_pct: Numeric | null
  max_drawdown_pct: Numeric | null
  num_trades: number | null
}

export interface EquityCurvePoint {
  timestamp: ISODateString
  cash: Numeric
  positions_value: Numeric
  equity: Numeric
  cumulative_return_pct: Numeric
  drawdown_pct: Numeric
}

export interface BacktestMetrics {
  initial_capital: Numeric
  final_capital: Numeric
  net_profit: Numeric
  total_return_pct: Numeric
  benchmark_return_pct: Numeric | null
  num_trades: number
  wins: number
  losses: number
  win_rate: Numeric
  average_win: Numeric
  average_loss: Numeric
  largest_win: Numeric
  largest_loss: Numeric
  gross_profit: Numeric
  gross_loss: Numeric
  profit_factor: Numeric | null
  expectancy: Numeric
  max_drawdown: Numeric
  max_drawdown_pct: Numeric
  sharpe_ratio: Numeric | null
  sortino_ratio: Numeric | null
  total_fees: Numeric
  total_slippage: Numeric
  average_holding_seconds: Numeric
  exposure_pct: Numeric
}

export interface BacktestTrade {
  symbol: string
  side: string
  quantity: Numeric
  entry_time: ISODateString
  entry_price: Numeric
  exit_time: ISODateString
  exit_price: Numeric
  gross_pnl: Numeric
  fees: Numeric
  slippage: Numeric
  net_pnl: Numeric
  return_pct: Numeric
  holding_period_seconds: number
  exit_reason: string
}

export interface MonthlyReturn {
  month: string
  return_pct: Numeric
}

export interface BacktestResult {
  backtest_id: string
  engine_version: string | null
  strategy_config: Record<string, unknown> | null
  metrics: BacktestMetrics
  equity_curve: EquityCurvePoint[]
  drawdown_curve: { timestamp: ISODateString; drawdown_pct: Numeric }[]
  monthly_returns: MonthlyReturn[]
  trades: BacktestTrade[]
}
