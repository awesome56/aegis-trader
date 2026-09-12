import type { Numeric } from '~/types/api'

export interface RawPortfolioSummary {
  portfolio_id: string
  currency: string
  equity: Numeric
  cash: Numeric
  buying_power: Numeric
  invested_amount: Numeric
  market_value: Numeric
  realized_pnl: Numeric
  unrealized_pnl: Numeric
  total_pnl: Numeric
  daily_pnl: Numeric | null
  daily_return_percent: Numeric | null
  total_return_percent: Numeric
  exposure_percent: Numeric
  position_count: number
  initial_capital: Numeric
  updated_at: string | null
}

export interface RawPositionValuation {
  id: string
  symbol: string
  asset_name: string | null
  asset_class: string | null
  sector: string | null
  quantity: Numeric
  average_entry_price: Numeric
  current_price: Numeric | null
  market_value: Numeric
  cost_basis: Numeric
  weight_percent: Numeric
  unrealized_pnl: Numeric
  unrealized_return_percent: Numeric
  realized_pnl: Numeric
  opened_at: string
  updated_at: string | null
  price_timestamp: string | null
  price_stale: boolean
}

export interface RawSnapshotPoint {
  snapshot_time: string
  equity: Numeric
  cash: Numeric
  market_value: Numeric
  realized_pnl: Numeric
  unrealized_pnl: Numeric
  total_return_percent: Numeric
  daily_pnl: Numeric
  exposure_percent: Numeric
  position_count: number
}

export interface RawPortfolioHistory {
  range: string
  start: string | null
  end: string | null
  point_count: number
  downsampled: boolean
  drawdown_percent: Numeric
  points: RawSnapshotPoint[]
}

export interface RawRiskUtilization {
  key: string
  current: Numeric
  limit: Numeric
  utilization_percent: Numeric
  status: string
  unit: string
}

export interface RawSignal {
  id: string
  strategy_id: string
  strategy_key: string | null
  strategy_name: string | null
  symbol: string
  direction: string
  strength: Numeric
  confidence: Numeric
  price: Numeric | null
  timeframe: string
  time_horizon: string | null
  market_regime: string | null
  indicators: Record<string, Numeric> | null
  signal_time: string
  data_timestamp: string | null
  expires_at: string | null
}

export interface RawDashboard {
  portfolio: RawPortfolioSummary
  trading_mode: string
  trading_state: string
  broker_provider: string
  broker_status: string
  market_data_provider: string
  market_data_status: string
  market_is_open: boolean
  market_session: string
  risk_status: string
  risk_utilizations: RawRiskUtilization[]
  recent_signals: RawSignal[]
  realtime_connections: number
  unread_notifications: number
  drawdown_percent: Numeric
  recent_orders: unknown[]
  recent_notifications: unknown[]
  availability: Record<string, boolean>
}

export interface RawTrade {
  id: string
  symbol: string
  side: string
  quantity: Numeric
  entry_price: Numeric
  exit_price: Numeric | null
  pnl: Numeric
  fees: Numeric
  return_pct: Numeric
  strategy_id: string | null
  proposal_id: string | null
  order_id: string | null
  opened_at: string
  closed_at: string | null
}

export interface RawTradePage {
  items: RawTrade[]
  total: number
  page: number
  page_size: number
}

export interface RawProposal {
  id: string
  portfolio_id: string
  strategy_id: string | null
  strategy_signal_id: string | null
  symbol: string
  asset_class: string
  action: string
  order_type: string
  source: string
  status: string
  proposed_quantity: Numeric
  proposed_position_percentage: Numeric | null
  requested_notional: Numeric | null
  entry_price: Numeric | null
  limit_price: Numeric | null
  stop_price: Numeric | null
  stop_loss: Numeric | null
  take_profit: Numeric | null
  confidence: Numeric
  time_horizon: string
  reasoning_summary: string | null
  market_regime: string | null
  failure_reason: string | null
  expires_at: string | null
  decided_at: string | null
  executed_at: string | null
  created_at: string
  updated_at: string
}

export interface RawProposalPage {
  items: RawProposal[]
  total: number
  limit: number
  offset: number
}
