import type { AgentDecision, AgentStatus } from '~/types/agent'
import type { PageParams, Paginated } from '~/types/api'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockAgentStatus, mockDecisions } from '~/mocks'

/** Agent surface is a placeholder until Backend Phase 9. Proposals live in `/proposals`. */
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
}
