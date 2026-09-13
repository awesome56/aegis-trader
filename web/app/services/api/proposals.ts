import type {
  ExecutionOutcome,
  ProposalCreateInput,
  ProposalDetail,
  TradeProposal,
} from '~/types/agent'
import type { PageParams, Paginated } from '~/types/api'
import { api } from './client'
import { isMockEnabled } from './config'
import {
  toExecutionOutcome,
  toProposal,
  toProposalDetail,
  toProposalPage,
  toRiskEvaluation,
} from './adapters'
import type {
  RawExecutionOutcome,
  RawProposal,
  RawProposalDetail,
  RawProposalEvaluation,
  RawProposalPage,
} from './adapters/raw'
import { mockProposals } from '~/mocks'

export interface ProposalEvaluationResult {
  proposal: TradeProposal
  evaluation: import('~/types/agent').RiskEvaluation
}

function optional(input: ProposalCreateInput): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    symbol: input.symbol,
    side: input.side,
    order_type: input.order_type,
  }
  const keys: (keyof ProposalCreateInput)[] = [
    'quantity',
    'notional',
    'limit_price',
    'stop_price',
    'stop_loss',
    'take_profit',
    'strategy_signal_id',
    'time_horizon',
    'confidence',
    'reasoning_summary',
    'idempotency_key',
  ]
  for (const key of keys) {
    const value = input[key]
    if (value !== undefined && value !== null && value !== '') payload[key] = value
  }
  return payload
}

function listQuery(params: PageParams): Record<string, unknown> {
  const limit = Number(params.limit ?? params.pageSize ?? 25)
  const page = Number(params.page ?? 1)
  const offset = Number(params.offset ?? (page - 1) * limit)
  const query: Record<string, unknown> = { limit, offset }
  if (params.status) query.status = params.status
  return query
}

export const proposalsService = {
  list: async (params: PageParams = {}): Promise<Paginated<TradeProposal>> => {
    if (isMockEnabled()) {
      const items = mockProposals()
      return { items, total: items.length, page: 1, pageSize: items.length || 1 }
    }
    return toProposalPage(await api.get<RawProposalPage>('/proposals', { query: listQuery(params) }))
  },
  get: async (id: string): Promise<ProposalDetail> => {
    if (isMockEnabled()) throw new Error('Proposal detail is unavailable in mock mode')
    return toProposalDetail(await api.get<RawProposalDetail>(`/proposals/${id}`))
  },
  create: async (input: ProposalCreateInput): Promise<TradeProposal> => {
    if (isMockEnabled()) throw new Error('Proposal creation is unavailable in mock mode')
    return toProposal(await api.post<RawProposal>('/proposals', optional(input)))
  },
  evaluate: async (id: string): Promise<ProposalEvaluationResult> => {
    if (isMockEnabled()) throw new Error('Proposal evaluation is unavailable in mock mode')
    const raw = await api.post<RawProposalEvaluation>(`/proposals/${id}/evaluate`)
    return { proposal: toProposal(raw.proposal), evaluation: toRiskEvaluation(raw.evaluation) }
  },
  execute: async (id: string): Promise<ExecutionOutcome> => {
    if (isMockEnabled()) throw new Error('Proposal execution is unavailable in mock mode')
    return toExecutionOutcome(await api.post<RawExecutionOutcome>(`/proposals/${id}/execute`))
  },
  cancel: async (id: string): Promise<TradeProposal> => {
    if (isMockEnabled()) throw new Error('Proposal cancellation is unavailable in mock mode')
    return toProposal(await api.post<RawProposal>(`/proposals/${id}/cancel`))
  },
}
