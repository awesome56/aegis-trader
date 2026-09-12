import type { ISODateString, Numeric } from './api'
import type { MarketRegime } from './market'

export type OrderAction = 'BUY' | 'SELL' | 'HOLD' | 'CLOSE' | 'REDUCE'
export type ProposalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'EXECUTED' | 'CANCELLED'
export type RiskDecision = 'APPROVED' | 'APPROVED_WITH_WARNINGS' | 'REJECTED'
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

/** Concise, structured decision record — never hidden chain-of-thought. */
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

export interface TradeProposal {
  id: string
  symbol: string
  asset_class: string
  action: OrderAction
  order_type: string
  proposed_quantity: Numeric
  proposed_position_pct: Numeric
  entry_price: Numeric | null
  stop_loss: Numeric | null
  take_profit: Numeric | null
  risk_reward_ratio: Numeric | null
  confidence: Numeric
  time_horizon: TimeHorizon
  strategy_id: string | null
  strategy_name: string | null
  reasoning_summary: string | null
  status: ProposalStatus
  risk_decision: RiskDecision | null
  created_at: ISODateString
  expires_at: ISODateString
}

/** The full auditable pipeline for a proposal (a core product view). */
export interface ProposalPipeline {
  proposal: TradeProposal
  signals: import('./strategy').StrategySignal[]
  decision: AgentDecision | null
  risk_evaluation: ProposalRiskEvaluation | null
  order: import('./order').Order | null
  executions: import('./order').Execution[]
}

export interface ProposalRiskEvaluation {
  id: string
  decision: RiskDecision
  risk_score: Numeric
  approved_quantity: Numeric | null
  risk_reward_ratio: Numeric | null
  checks: { name: string; passed: boolean; detail?: string }[]
  reasons: string[]
  warnings: string[]
  evaluated_at: ISODateString
}
