import type { MessageResponse } from '~/types/api'
import type { Strategy, StrategyDetail } from '~/types/strategy'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockStrategies, mockStrategy } from '~/mocks'

/**
 * BACKEND REQUIREMENT (not yet implemented):
 *   GET /strategies
 *   GET /strategies/{id}
 *   POST /strategies/{id}/enable
 *   POST /strategies/{id}/disable
 *
 * Enable/disable changes automated trading behaviour and must always be
 * confirmed in the UI (see ConfirmationDialog).
 */
export const strategiesService = {
  list: async (): Promise<Strategy[]> => {
    if (isMockEnabled()) return mockStrategies()
    return api.get<Strategy[]>('/strategies')
  },
  get: async (id: string): Promise<StrategyDetail> => {
    if (isMockEnabled()) {
      const detail = mockStrategy(id)
      if (!detail) throw new Error(`Strategy ${id} not found (mock)`)
      return detail
    }
    return api.get<StrategyDetail>(`/strategies/${id}`)
  },
  setEnabled: async (id: string, enabled: boolean): Promise<MessageResponse> => {
    if (isMockEnabled()) {
      return { detail: enabled ? 'Strategy enabled' : 'Strategy disabled' }
    }
    return api.post<MessageResponse>(`/strategies/${id}/${enabled ? 'enable' : 'disable'}`)
  },
}
