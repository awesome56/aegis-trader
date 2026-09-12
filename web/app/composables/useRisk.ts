import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { riskService } from '~/services/api/risk'
import type { PageParams, Paginated } from '~/types/api'
import type { RiskEvent, RiskLimit, RiskSettings, RiskStatus } from '~/types/risk'

export function useRiskStatus() {
  return useQuery<RiskStatus>({
    queryKey: queryKeys.riskStatus,
    queryFn: () => riskService.status(),
    staleTime: 10_000,
  })
}

export function useRiskLimits() {
  return useQuery<RiskLimit[]>({
    queryKey: queryKeys.riskLimits,
    queryFn: () => riskService.limits(),
    staleTime: 15_000,
  })
}

export function useRiskSettings() {
  return useQuery<RiskSettings>({
    queryKey: queryKeys.riskSettings,
    queryFn: () => riskService.settings(),
    staleTime: 60_000,
  })
}

export function useRiskEvents(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<RiskEvent>>({
    queryKey: computed(() => queryKeys.riskEvents(toValue(params))),
    queryFn: () => riskService.events(toValue(params)),
    staleTime: 15_000,
  })
}

export function useUpdateRiskSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (settings: Partial<RiskSettings>) => riskService.updateSettings(settings),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.riskSettings })
      void queryClient.invalidateQueries({ queryKey: queryKeys.riskLimits })
      void queryClient.invalidateQueries({ queryKey: queryKeys.riskStatus })
    },
  })
}
