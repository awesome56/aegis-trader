import type { PageParams, Paginated } from '~/types/api'
import type { RiskEvent, RiskLimit, RiskSettings, RiskStatus } from '~/types/risk'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockRiskEvents, mockRiskLimits, mockRiskSettings, mockRiskStatus } from '~/mocks'

/**
 * BACKEND REQUIREMENT (not yet implemented):
 *   GET /risk
 *   GET /risk/limits
 *   GET /risk/settings
 *   PUT /risk/settings   (write — validated server-side)
 *   GET /risk/events
 *
 * Risk decisions are never made in the browser; this is a read/configure view.
 */
export const riskService = {
  status: async (): Promise<RiskStatus> => {
    if (isMockEnabled()) return mockRiskStatus()
    return api.get<RiskStatus>('/risk')
  },
  limits: async (): Promise<RiskLimit[]> => {
    if (isMockEnabled()) return mockRiskLimits()
    return api.get<RiskLimit[]>('/risk/limits')
  },
  settings: async (): Promise<RiskSettings> => {
    if (isMockEnabled()) return mockRiskSettings()
    return api.get<RiskSettings>('/risk/settings')
  },
  updateSettings: async (settings: Partial<RiskSettings>): Promise<RiskSettings> => {
    if (isMockEnabled()) return { ...mockRiskSettings(), ...settings }
    return api.put<RiskSettings>('/risk/settings', settings)
  },
  events: async (params: PageParams = {}): Promise<Paginated<RiskEvent>> => {
    if (isMockEnabled()) {
      const items = mockRiskEvents()
      return { items, total: items.length, page: 1, pageSize: items.length }
    }
    return api.get<Paginated<RiskEvent>>('/risk/events', { query: params })
  },
}
