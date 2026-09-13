import type { AllocationBreakdown, PortfolioHistory, PortfolioRange, PortfolioSummary } from '~/types/portfolio'
import { api } from './client'
import { isMockEnabled } from './config'
import { toAllocationBreakdown, toPortfolioHistory, toPortfolioSummary } from './adapters'
import type { RawAllocationBreakdown, RawPortfolioHistory, RawPortfolioSummary } from './adapters/raw'
import { mockAllocation, mockPortfolio, mockPortfolioHistory } from '~/mocks'

export const portfolioService = {
  get: async (): Promise<PortfolioSummary> => {
    if (isMockEnabled()) return mockPortfolio()
    return toPortfolioSummary(await api.get<RawPortfolioSummary>('/portfolio'))
  },
  history: async (range: PortfolioRange): Promise<PortfolioHistory> => {
    if (isMockEnabled()) {
      const days = range === '1D' ? 1 : range === '1W' ? 7 : range === '1M' ? 30 : 90
      return { range, currency: 'USD', points: mockPortfolioHistory(days) }
    }
    return toPortfolioHistory(
      await api.get<RawPortfolioHistory>('/portfolio/history', { query: { range } }),
    )
  },
  allocation: async (): Promise<AllocationBreakdown> => {
    if (isMockEnabled()) return mockAllocation()
    return toAllocationBreakdown(await api.get<RawAllocationBreakdown>('/portfolio/allocation'))
  },
}
