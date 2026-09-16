import type { ISODateString, Numeric } from './api'
import type { MarketRegime } from './market'
import type { Execution, Order, OrderSide, OrderType } from './order'

export type OrderAction = 'BUY' | 'SELL' | 'HOLD' | 'CLOSE' | 'REDUCE'

export type ProposalStatus =
  | 'DRAFT'
  | 'PENDING'
  | 'PENDING_RISK'
  | 'RISK_APPROVED'
  | 'RISK_REJECTED'
  | 'READY_FOR_EXECUTION'
  | 'EXECUTING'
  | 'EXECUTED'
  | 'APPROVED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'CANCELLED'
  | 'FAILED'

export type ProposalSource = 'MANUAL' | 'STRATEGY' | 'AGENT'

export type RiskDecision = 'APPROVED' | 'APPROVED_WITH_WARNINGS' | 'REJECTED' | 'ERROR'

export type RuleSeverity = 'INFO' | 'WARNING' | 'BLOCKING'

export type TimeHorizon = 'INTRADAY' | 'SWING' | 'POSITION' | 'LONG_TERM'

export interface AgentStatus {
  enabled: boolean
  running: boolean
  last_analysis_at: ISODateString | null
  next_run_at: ISODateString | null
  symbols_under_analysis: string[]
  decisions_today: number
  proposals_today: number
  approved_today: number
  rejected_today: number
  error_count_today: number
  last_error: string | null
}

export interface DecisionEvidence {
  label: string
  value: string
  sentiment?: 'positive' | 'negative' | 'neutral'
}

export interface AgentDecision {
  id: string
  run_id: string | null
  symbol: string
  action: OrderAction
  confidence: Numeric
  market_regime: MarketRegime | null
  reasoning_summary: string | null
  evidence: DecisionEvidence[]
  risk_decision: RiskDecision | null
  proposal_id: string | null
  created_at: ISODateString
}

/** Deterministic, manual or strategy-sourced trade proposal (Phase 7). */
export interface TradeProposal {
  id: string
  portfolio_id: string
  strategy_id: string | null
  strategy_signal_id: string | null
  symbol: string
  asset_class: string
  action: OrderAction
  order_type: OrderType
  source: ProposalSource
  status: ProposalStatus
  proposed_quantity: Numeric
  proposed_position_percentage: Numeric | null
  requested_notional: Numeric | null
  entry_price: Numeric | null
  limit_price: Numeric | null
  stop_price: Numeric | null
  stop_loss: Numeric | null
  take_profit: Numeric | null
  confidence: Numeric
  time_horizon: TimeHorizon
  reasoning_summary: string | null
  market_regime: MarketRegime | null
  failure_reason: string | null
  expires_at: ISODateString | null
  decided_at: ISODateString | null
  executed_at: ISODateString | null
  created_at: ISODateString
  updated_at: ISODateString
}

export interface ProposalRuleResult {
  key: string
  passed: boolean
  severity: RuleSeverity
  message: string
  current: Numeric | null
  limit: Numeric | null
  utilization_percent: Numeric | null
  metadata: Record<string, unknown> | null
}

/** A persisted deterministic risk evaluation. */
export interface RiskEvaluation {
  id: string
  decision: RiskDecision
  symbol: string
  side: OrderSide
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
  rules: ProposalRuleResult[]
  reasons: string[]
  warnings: string[]
  evaluated_at: ISODateString
}

export interface ProposalDetail {
  proposal: TradeProposal
  evaluations: RiskEvaluation[]
  orders: Order[]
  executions: Execution[]
}

export interface ExecutionOutcome {
  proposal_id: string
  executed: boolean
  status: string
  order_id: string | null
  final_evaluation_id: string | null
  final_decision: string | null
  reason: string | null
}

export interface ProposalCreateInput {
  symbol: string
  side: OrderSide
  order_type: OrderType
  quantity?: string
  notional?: string
  limit_price?: string
  stop_price?: string
  stop_loss?: string
  take_profit?: string
  strategy_signal_id?: string | null
  time_horizon?: TimeHorizon
  confidence?: string
  reasoning_summary?: string | null
  idempotency_key?: string
}

// --- Phase 9: TradingAnalysisAgent -----------------------------------------

export type AgentMode = 'ANALYSIS_ONLY' | 'PROPOSE' | 'AUTO_TRADE'

export type AgentRunStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

export interface AgentRun {
  id: string
  status: AgentRunStatus
  provider: string | null
  model: string | null
  mode: AgentMode
  symbols: string[]
  prompt: string | null
  error: string | null
  latency_ms: number | null
  tokens_used: number | null
  usage: Record<string, unknown> | null
  proposal_id: string | null
  started_at: ISODateString | null
  completed_at: ISODateString | null
  created_at: ISODateString
}

export interface AgentRuntimeStatus {
  enabled: boolean
  default_mode: string
  provider: string | null
  model: string | null
  provider_status: string
  provider_config_id: string | null
  running: number
  runs_today: number
  recent_failures: number
  last_run: AgentRun | null
}

export interface AgentDecisionRecord {
  id: string
  agent_run_id: string | null
  symbol: string
  action: OrderAction
  confidence: Numeric
  reasoning_summary: string | null
  evidence: AgentEvidenceRecord[] | null
  concerns: string[] | null
  proposal_recommended: boolean
  market_regime: MarketRegime | null
  strategy_signal_ids: string[] | null
  proposal_id: string | null
  created_at: ISODateString
}

export interface AgentEvidenceRecord {
  type: string
  source: string
  direction?: string | null
  confidence?: Numeric | null
  data?: Record<string, unknown>
}

export interface AnalyzeInput {
  symbol: string
  timeframe: string
  mode: AgentMode
  provider_config_id?: string
  broker_account_id?: string
  prompt?: string
}
