import type {
  OrderAction,
  ProposalDetail,
  ProposalRuleResult,
  ProposalSource,
  ProposalStatus,
  RiskEvaluation,
  TimeHorizon,
  TradeProposal,
  ExecutionOutcome,
} from '~/types/agent'
import type { Paginated } from '~/types/api'
import type { OrderSide, OrderType } from '~/types/order'
import { iso, isoOrNull, num, numOrNull } from './common'
import { toExecution, toOrder } from './orders'
import type {
  RawProposal,
  RawProposalDetail,
  RawProposalPage,
  RawExecutionOutcome,
  RawRiskEvaluation,
  RawRuleResult,
} from './raw'

export function toProposal(raw: RawProposal): TradeProposal {
  return {
    id: raw.id,
    portfolio_id: raw.portfolio_id,
    strategy_id: raw.strategy_id,
    strategy_signal_id: raw.strategy_signal_id,
    symbol: raw.symbol,
    asset_class: raw.asset_class,
    action: raw.action as OrderAction,
    order_type: raw.order_type as OrderType,
    source: raw.source as ProposalSource,
    status: raw.status as ProposalStatus,
    proposed_quantity: num(raw.proposed_quantity),
    proposed_position_percentage: numOrNull(raw.proposed_position_percentage),
    requested_notional: numOrNull(raw.requested_notional),
    entry_price: raw.entry_price,
    limit_price: raw.limit_price,
    stop_price: raw.stop_price,
    stop_loss: raw.stop_loss,
    take_profit: raw.take_profit,
    confidence: num(raw.confidence),
    time_horizon: raw.time_horizon as TimeHorizon,
    reasoning_summary: raw.reasoning_summary,
    market_regime: (raw.market_regime as TradeProposal['market_regime']) ?? null,
    failure_reason: raw.failure_reason,
    expires_at: isoOrNull(raw.expires_at),
    decided_at: isoOrNull(raw.decided_at),
    executed_at: isoOrNull(raw.executed_at),
    created_at: iso(raw.created_at),
    updated_at: iso(raw.updated_at),
  }
}

export function toProposalPage(raw: RawProposalPage): Paginated<TradeProposal> {
  const pageSize = raw.limit > 0 ? raw.limit : raw.items.length || 1
  return {
    items: raw.items.map(toProposal),
    total: raw.total,
    page: Math.floor(raw.offset / pageSize) + 1,
    pageSize,
  }
}

function toRule(raw: RawRuleResult): ProposalRuleResult {
  return {
    key: raw.key,
    passed: raw.passed,
    severity: raw.severity as ProposalRuleResult['severity'],
    message: raw.message,
    current: raw.current,
    limit: raw.limit,
    utilization_percent: raw.utilization_percent,
    metadata: raw.metadata,
  }
}

export function toRiskEvaluation(raw: RawRiskEvaluation): RiskEvaluation {
  return {
    id: raw.id,
    decision: raw.decision as RiskEvaluation['decision'],
    symbol: raw.symbol,
    side: raw.side as OrderSide,
    source: raw.source,
    requested_quantity: num(raw.requested_quantity),
    approved_quantity: raw.approved_quantity,
    requested_notional: num(raw.requested_notional),
    approved_notional: raw.approved_notional,
    entry_price: raw.entry_price,
    stop_loss: raw.stop_loss,
    take_profit: raw.take_profit,
    estimated_risk_amount: raw.estimated_risk_amount,
    risk_reward_ratio: raw.risk_reward_ratio,
    portfolio_exposure_before_percent: num(raw.portfolio_exposure_before_percent),
    portfolio_exposure_after_percent: raw.portfolio_exposure_after_percent,
    risk_score: num(raw.risk_score),
    rules: (raw.rules ?? []).map(toRule),
    reasons: raw.reasons ?? [],
    warnings: raw.warnings ?? [],
    evaluated_at: iso(raw.evaluated_at),
  }
}

export function toProposalDetail(raw: RawProposalDetail): ProposalDetail {
  return {
    proposal: toProposal(raw.proposal),
    evaluations: (raw.evaluations ?? []).map(toRiskEvaluation),
    orders: (raw.orders ?? []).map(toOrder),
    executions: (raw.executions ?? []).map(toExecution),
  }
}

export function toExecutionOutcome(raw: RawExecutionOutcome): ExecutionOutcome {
  return {
    proposal_id: raw.proposal_id,
    executed: raw.executed,
    status: raw.status,
    order_id: raw.order_id,
    final_evaluation_id: raw.final_evaluation_id,
    final_decision: raw.final_decision,
    reason: raw.reason,
  }
}
