import type { AllocationBreakdown, PortfolioHistory, PortfolioRange, PortfolioSummary } from '~/types/portfolio'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockAllocation, mockPortfolio, mockPortfolioHistory } from '~/mocks'

/**
 * BACKEND REQUIREMENT (not yet implemented):
 *   GET /portfolio
 *   GET /portfolio/history?range=1D|1W|1M|3M|6M|YTD|1Y|ALL
 *   GET /portfolio/allocation
 */
export const portfolioService = {
  get: async (): Promise<PortfolioSummary> => {
    if (isMockEnabled()) return mockPortfolio()
    return api.get<PortfolioSummary>('/portfolio')
  },
  history: async (range: PortfolioRange): Promise<PortfolioHistory> => {
    if (isMockEnabled()) {
      const days = range === '1D' ? 1 : range === '1W' ? 7 : range === '1M' ? 30 : 90
      return { range, currency: 'USD', points: mockPortfolioHistory(days) }
    }
    return api.get<PortfolioHistory>('/portfolio/history', { query: { range } })
  },
  allocation: async (): Promise<AllocationBreakdown> => {
    if (isMockEnabled()) return mockAllocation()
    return api.get<AllocationBreakdown>('/portfolio/allocation')
  },
}
