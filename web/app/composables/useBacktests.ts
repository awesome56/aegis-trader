import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { backtestsService } from '~/services/api/backtests'
import type { PageParams, Paginated } from '~/types/api'
import type { Backtest, BacktestConfig, BacktestResult } from '~/types/backtest'

export function useBacktests(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<Backtest>>({
    queryKey: computed(() => queryKeys.backtests(toValue(params))),
    queryFn: () => backtestsService.list(toValue(params)),
    staleTime: 30_000,
  })
}

export function useBacktest(id: MaybeRefOrGetter<string>) {
  return useQuery<Backtest>({
    queryKey: computed(() => queryKeys.backtest(toValue(id))),
    queryFn: () => backtestsService.get(toValue(id)),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

export function useBacktestResult(id: MaybeRefOrGetter<string>) {
  return useQuery<BacktestResult>({
    queryKey: computed(() => queryKeys.backtestResult(toValue(id))),
    queryFn: () => backtestsService.result(toValue(id)),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

/** Submit a backtest configuration to the backend (all computation is server-side). */
export function useRunBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (config: BacktestConfig) => backtestsService.run(config),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.backtests() })
    },
  })
}
