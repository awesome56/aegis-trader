import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { portfolioService } from '~/services/api/portfolio'
import type { AllocationBreakdown, PortfolioHistory, PortfolioRange, PortfolioSummary } from '~/types/portfolio'

export function usePortfolio() {
  return useQuery<PortfolioSummary>({
    queryKey: queryKeys.portfolio,
    queryFn: () => portfolioService.get(),
    staleTime: 10_000,
  })
}

export function usePortfolioHistory(range: MaybeRefOrGetter<PortfolioRange> = '1M') {
  return useQuery<PortfolioHistory>({
    queryKey: computed(() => queryKeys.portfolioHistory(toValue(range))),
    queryFn: () => portfolioService.history(toValue(range)),
    staleTime: 30_000,
  })
}

export function useAllocation() {
  return useQuery<AllocationBreakdown>({
    queryKey: queryKeys.allocation,
    queryFn: () => portfolioService.allocation(),
    staleTime: 60_000,
  })
}
