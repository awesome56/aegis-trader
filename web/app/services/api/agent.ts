import type { PageParams, Paginated } from '~/types/api'
import type { AgentDecision, AgentStatus, ProposalPipeline, TradeProposal } from '~/types/agent'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockAgentStatus, mockDecisions, mockProposalPipeline, mockProposals } from '~/mocks'

/**
 * BACKEND REQUIREMENT (not yet implemented):
 *   GET /agent/status
 *   GET /agent/decisions
 *   GET /proposals
 *   GET /proposals/{id} (returns the full pipeline)
 *
 * The frontend only ever reads agent output. It cannot trigger analyses,
 * approve proposals, or influence the risk engine.
 */
export const agentService = {
  status: async (): Promise<AgentStatus> => {
    if (isMockEnabled()) return mockAgentStatus()
    return api.get<AgentStatus>('/agent/status')
  },
  decisions: async (params: PageParams = {}): Promise<Paginated<AgentDecision>> => {
    if (isMockEnabled()) {
      const items = mockDecisions()
      return { items, total: items.length, page: 1, pageSize: items.length }
    }
    return api.get<Paginated<AgentDecision>>('/agent/decisions', { query: params })
  },
  proposals: async (params: PageParams = {}): Promise<Paginated<TradeProposal>> => {
    if (isMockEnabled()) {
      const items = mockProposals()
      return { items, total: items.length, page: 1, pageSize: items.length }
    }
    return api.get<Paginated<TradeProposal>>('/proposals', { query: params })
  },
  proposal: async (id: string): Promise<TradeProposal> => {
    if (isMockEnabled()) {
      const found = mockProposals().find((proposal) => proposal.id === id)
      if (!found) throw new Error(`Proposal ${id} not found (mock)`)
      return found
    }
    return api.get<TradeProposal>(`/proposals/${id}`)
  },
  pipeline: async (id: string): Promise<ProposalPipeline> => {
    if (isMockEnabled()) {
      const pipeline = mockProposalPipeline(id)
      if (!pipeline) throw new Error(`Proposal ${id} not found (mock)`)
      return pipeline
    }
    return api.get<ProposalPipeline>(`/proposals/${id}/pipeline`)
  },
}
