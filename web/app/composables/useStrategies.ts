import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { strategiesService } from '~/services/api/strategies'
import type { Strategy, StrategyDetail } from '~/types/strategy'

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

/**
 * Enabling/disabling a strategy changes automated trading behaviour, so callers
 * must confirm before invoking this mutation (see ConfirmationDialog).
 */
export function useSetStrategyEnabled() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      strategiesService.setEnabled(id, enabled),
    onSuccess: (_result, variables) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.strategies })
      void queryClient.invalidateQueries({ queryKey: queryKeys.strategy(variables.id) })
    },
  })
}
