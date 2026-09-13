import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { strategiesService, type EvaluateStrategyInput } from '~/services/api/strategies'
import type { Strategy, StrategyDetail, StrategySignalPage } from '~/types/strategy'
import type { PageParams } from '~/types/api'

export function useStrategies() {
  return useQuery<Strategy[]>({
    queryKey: queryKeys.strategies,
    queryFn: () => strategiesService.list(),
    staleTime: 30_000,
  })
}

export function useStrategy(id: MaybeRefOrGetter<string>) {
  return useQuery<StrategyDetail>({
    queryKey: computed(() => queryKeys.strategy(toValue(id))),
    queryFn: () => strategiesService.get(toValue(id)),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

export function useStrategySignals(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<StrategySignalPage>({
    queryKey: computed(() => queryKeys.strategySignals(toValue(params))),
    queryFn: () => strategiesService.signals(toValue(params)),
    staleTime: 15_000,
  })
}

/**
 * Enabling/disabling a strategy changes automated evaluation, so callers must
 * confirm before invoking this mutation (see ConfirmationDialog).
 */
export function useSetStrategyEnabled() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      enabled ? strategiesService.enable(id) : strategiesService.disable(id),
    onSuccess: (_result, variables) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.strategies })
      void queryClient.invalidateQueries({ queryKey: queryKeys.strategy(variables.id) })
      void queryClient.invalidateQueries({ queryKey: ['strategies', 'signals'] })
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard })
      void queryClient.invalidateQueries({ queryKey: queryKeys.activityRoot })
    },
  })
}

export function useEvaluateStrategies() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: EvaluateStrategyInput) => strategiesService.evaluate(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['strategies', 'signals'] })
      void queryClient.invalidateQueries({ queryKey: queryKeys.strategies })
      void queryClient.invalidateQueries({ queryKey: queryKeys.markets })
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard })
      void queryClient.invalidateQueries({ queryKey: queryKeys.activityRoot })
    },
  })
}
