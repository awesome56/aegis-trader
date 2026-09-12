import type { DashboardData } from '~/types/dashboard'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockDashboard } from '~/mocks'

/** BACKEND REQUIREMENT: `GET /dashboard` (not yet implemented). */
export const dashboardService = {
  get: async (): Promise<DashboardData> => {
    if (isMockEnabled()) return mockDashboard()
    return api.get<DashboardData>('/dashboard')
  },
}
