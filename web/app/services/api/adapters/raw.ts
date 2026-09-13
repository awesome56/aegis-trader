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

export interface RawAllocationSlice {
  label: string
  value: Numeric
  weight_percent: Numeric
}

export interface RawAllocationBreakdown {
  total_equity: Numeric
  cash_weight_percent: Numeric
  by_symbol: RawAllocationSlice[]
  by_asset_class: RawAllocationSlice[]
  by_sector: RawAllocationSlice[]
}

export interface RawRiskUtilization {
  key: string
  current: Numeric
  limit: Numeric
  utilization_percent: Numeric
  status: string
  unit: string
}

export interface RawRiskOverview {
  status: string
  trading_state: string
  equity: Numeric
  cash: Numeric
  buying_power: Numeric
  portfolio_exposure_percent: Numeric
  daily_pnl: Numeric | null
  daily_loss_limit_percent: Numeric
  current_drawdown_percent: Numeric
  max_drawdown_percent: Numeric
  open_positions: number
  max_open_positions: number
  trades_today: number
  max_trades_per_day: number
  utilizations: RawRiskUtilization[]
  updated_at: string
}

export interface RawRiskSettings {
  is_enabled: boolean
  max_position_percent: Numeric
  max_portfolio_exposure_percent: Numeric
  max_open_positions: number
  max_daily_loss_percent: Numeric
  max_drawdown_percent: Numeric
  max_trades_per_day: number
  max_risk_per_trade_percent: Numeric
  min_strategy_confidence: Numeric
  min_reward_risk_ratio: Numeric
  require_stop_loss: boolean
  require_strategy_signal: boolean
  max_sector_exposure_percent: Numeric
  max_asset_class_exposure_percent: Numeric
  unknown_sector_policy: string
  daily_loss_include_unrealized: boolean
  commission_buffer_bps: Numeric
}

export interface RawRiskEvent {
  id: string
  event_type: string
  severity: string
  source: string
  message: string
  actor: string | null
  payload: Record<string, unknown> | null
  occurred_at: string
}

export interface RawTradingStatus {
  trading_state: string
  previous_state: string | null
  reason: string | null
  actor: string | null
  changed_at: string | null
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

export interface RawStrategy {
  id: string
  key: string
  name: string
  description: string | null
  strategy_type: string
  is_enabled: boolean
  timeframe: string
  priority: number
  parameters: Record<string, unknown> | null
  asset_classes: string[] | null
  signal_count: number
  last_signal_at: string | null
  created_at: string
  updated_at: string
}

export interface RawStrategyDetail extends RawStrategy {
  recent_signals: RawSignal[]
}

export interface RawSignalPage {
  items: RawSignal[]
  total: number
  page: number
  page_size: number
}

export interface RawSignalEvidence {
  strategy_key: string
  strategy_name: string
  symbol: string
  direction: string
  strength: Numeric
  confidence: Numeric
  price: Numeric | null
  timeframe: string
  time_horizon: string
  market_regime: string
  indicators: Record<string, Numeric>
  generated_at: string
  data_timestamp: string
  expires_at: string
}

export interface RawStrategyEvaluation {
  strategy_key: string
  strategy_name: string
  symbol: string
  timeframe: string
  status: string
  reason: string
  signal: RawSignalEvidence | null
}

export interface RawNotification {
  id: string
  category: string
  severity: string
  title: string
  message: string
  is_read: boolean
  read_at: string | null
  payload: Record<string, unknown> | null
  created_at: string
}

export interface RawNotificationPage {
  items: RawNotification[]
  total: number
  page: number
  page_size: number
}

export interface RawUnreadCount {
  unread: number
}

export interface RawActivityEvent {
  id: string
  event_type: string
  severity: string
  source: string
  message: string
  actor: string | null
  correlation_id: string | null
  payload: Record<string, unknown> | null
  occurred_at: string
}

export interface RawActivityPage {
  items: RawActivityEvent[]
  total: number
  page: number
  page_size: number
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

export interface RawMarketStatus {
  market: string
  is_open: boolean
  session: string
  opens_at: string | null
  closes_at: string | null
  timestamp: string
  provider: string
}

export interface RawMarketOverviewItem {
  symbol: string
  name: string | null
  price: Numeric | null
  change_pct: Numeric | null
  volume: number | null
  signal_direction: string | null
  strategy: string | null
  confidence: Numeric | null
  market_regime: string | null
  quote_time: string | null
  is_stale: boolean
}

export interface RawMarketOverview {
  status: RawMarketStatus
  items: RawMarketOverviewItem[]
}

export interface RawAssetSearch {
  symbol: string
  name: string | null
  asset_class: string
  exchange: string | null
  currency: string
  provider: string
}

export interface RawQuote {
  symbol: string
  bid: Numeric | null
  ask: Numeric | null
  last: Numeric
  open: Numeric | null
  high: Numeric | null
  low: Numeric | null
  previous_close: Numeric | null
  volume: number | null
  currency: string
  provider: string
  market_timestamp: string
  received_at: string
  age_seconds: number
  is_stale: boolean
}

export interface RawCandle {
  open_time: string
  close_time: string | null
  open: Numeric
  high: Numeric
  low: Numeric
  close: Numeric
  volume: number | null
  trade_count: number | null
  vwap: Numeric | null
}

export interface RawCandleSeries {
  symbol: string
  timeframe: string
  provider: string
  candles: RawCandle[]
  is_stale: boolean | null
  age_seconds: number | null
}

export interface RawRuleResult {
  key: string
  passed: boolean
  severity: string
  message: string
  current: Numeric | null
  limit: Numeric | null
  utilization_percent: Numeric | null
  metadata: Record<string, unknown> | null
}

export interface RawRiskEvaluation {
  id: string
  decision: string
  symbol: string
  side: string
  source: string
  requested_quantity: Numeric
  approved_quantity: Numeric | null
  requested_notional: Numeric
  approved_notional: Numeric | null
  entry_price: Numeric | null
  stop_loss: Numeric | null
  take_profit: Numeric | null
  estimated_risk_amount: Numeric | null
  risk_reward_ratio: Numeric | null
  portfolio_exposure_before_percent: Numeric
  portfolio_exposure_after_percent: Numeric | null
  risk_score: Numeric
  rules: RawRuleResult[]
  reasons: string[]
  warnings: string[]
  evaluated_at: string
}

export interface RawExecution {
  id: string
  order_id: string
  quantity: Numeric
  price: Numeric
  gross_amount: Numeric | null
  net_amount: Numeric | null
  fees: Numeric
  commission: Numeric
  slippage: Numeric
  broker_execution_id: string | null
  liquidity: string | null
  executed_at: string
}

export interface RawBrokerOrder {
  order_id: string
  broker_order_id: string | null
  client_order_id: string | null
  symbol: string
  side: string
  order_type: string
  time_in_force: string
  quantity: Numeric
  filled_quantity: Numeric
  remaining_quantity: Numeric
  limit_price: Numeric | null
  stop_price: Numeric | null
  average_fill_price: Numeric | null
  commission: Numeric
  status: string
  error_message: string | null
  created_at: string | null
  updated_at: string | null
  submitted_at: string | null
  filled_at: string | null
  cancelled_at: string | null
}

export interface RawBrokerOrderList {
  items: RawBrokerOrder[]
  total: number
}

export interface RawProposalDetail {
  proposal: RawProposal
  evaluations: RawRiskEvaluation[]
  orders: RawBrokerOrder[]
  executions: RawExecution[]
}

export interface RawProposalEvaluation {
  proposal: RawProposal
  evaluation: RawRiskEvaluation
}

export interface RawExecutionOutcome {
  proposal_id: string
  executed: boolean
  status: string
  order_id: string | null
  final_evaluation_id: string | null
  final_decision: string | null
  reason: string | null
}
