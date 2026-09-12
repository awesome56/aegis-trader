import type { OrderAction, ProposalStatus, TimeHorizon, TradeProposal } from '~/types/agent'
import type { Paginated } from '~/types/api'
import { iso, num } from './common'
import type { RawProposal, RawProposalPage } from './raw'

const STATUS: Record<string, ProposalStatus> = {
  DRAFT: 'PENDING',
  PENDING: 'PENDING',
  PENDING_RISK: 'PENDING',
  RISK_APPROVED: 'APPROVED',
  APPROVED: 'APPROVED',
  READY_FOR_EXECUTION: 'APPROVED',
  EXECUTING: 'APPROVED',
  RISK_REJECTED: 'REJECTED',
  REJECTED: 'REJECTED',
  FAILED: 'REJECTED',
  EXECUTED: 'EXECUTED',
  CANCELLED: 'CANCELLED',
  EXPIRED: 'EXPIRED',
}

export function toProposal(raw: RawProposal): TradeProposal {
  return {
    id: raw.id,
    symbol: raw.symbol,
    asset_class: raw.asset_class,
    action: raw.action as OrderAction,
    order_type: raw.order_type,
    proposed_quantity: num(raw.proposed_quantity),
    proposed_position_pct: num(raw.proposed_position_percentage),
    entry_price: raw.entry_price,
    stop_loss: raw.stop_loss,
    take_profit: raw.take_profit,
    risk_reward_ratio: null,
    confidence: num(raw.confidence),
    time_horizon: raw.time_horizon as TimeHorizon,
    strategy_id: raw.strategy_id,
    strategy_name: null,
    reasoning_summary: raw.reasoning_summary,
    status: STATUS[raw.status] ?? 'PENDING',
    risk_decision: null,
    created_at: iso(raw.created_at),
    expires_at: iso(raw.expires_at),
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
