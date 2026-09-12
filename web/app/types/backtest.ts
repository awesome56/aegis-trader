import type { ISODateString, Numeric } from './api'

export type BacktestStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface BacktestConfig {
  strategy_id: string
  symbols: string[]
  initial_capital: Numeric
  start_date: ISODateString
  end_date: ISODateString
  timeframe: string
  fees_pct?: Numeric
  slippage_pct?: Numeric
  benchmark_symbol?: string
  parameters?: Record<string, unknown>
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
  status: BacktestStatus
  created_at: ISODateString
  completed_at: ISODateString | null
  error: string | null
}

export interface EquityCurvePoint {
  time: ISODateString
  equity: Numeric
  benchmark: Numeric | null
  drawdown_pct: Numeric
}

export interface BacktestMetrics {
  initial_capital: Numeric
  final_capital: Numeric
  total_return_pct: Numeric
  benchmark_return_pct: Numeric | null
  max_drawdown_pct: Numeric
  sharpe_ratio: Numeric | null
  sortino_ratio: Numeric | null
  num_trades: number
  wins: number
  losses: number
  win_rate: Numeric
  average_win: Numeric
  average_loss: Numeric
  profit_factor: Numeric | null
  expectancy: Numeric | null
  exposure_pct: Numeric | null
  fees: Numeric
  slippage: Numeric
}

export interface BacktestTrade {
  symbol: string
  side: string
  quantity: Numeric
  entry_price: Numeric
  exit_price: Numeric
  pnl: Numeric
  return_pct: Numeric
  opened_at: ISODateString
  closed_at: ISODateString
}

export interface BacktestResult {
  backtest: Backtest
  metrics: BacktestMetrics
  equity_curve: EquityCurvePoint[]
  monthly_returns: { month: string; return_pct: Numeric }[]
  trades: BacktestTrade[]
}
