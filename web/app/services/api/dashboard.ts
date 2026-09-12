import type { DashboardData } from '~/types/dashboard'
import { api } from './client'
import { isMockEnabled } from './config'
import { toDashboardData } from './adapters'
import type {
  RawDashboard,
  RawPortfolioHistory,
  RawPositionValuation,
  RawProposalPage,
  RawTradePage,
} from './adapters/raw'
import { mockDashboard } from '~/mocks'

export const dashboardService = {
  get: async (): Promise<DashboardData> => {
    if (isMockEnabled()) return mockDashboard()

    const [dashboard, positions, history, trades, proposals] = await Promise.all([
      api.get<RawDashboard>('/dashboard'),
      api.get<RawPositionValuation[]>('/positions'),
      api.get<RawPortfolioHistory>('/portfolio/history', { query: { range: '1M' } }),
      api.get<RawTradePage>('/trades', { query: { page: 1, page_size: 5 } }),
      api.get<RawProposalPage>('/proposals', { query: { limit: 5, offset: 0 } }),
    ])

    return toDashboardData({ dashboard, positions, history, trades, proposals })
  },
}
