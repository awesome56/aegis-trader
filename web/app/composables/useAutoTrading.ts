import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { queryKeys } from '~/services/api/keys'
import { autoTradingService } from '~/services/api/autoTrading'
import { brokersService } from '~/services/api/brokers'
import type {
  AutoTradingPolicy,
  AutoTradingStatus,
  BrokerConnection,
  BrokerConnectionCreateInput,
} from '~/types/autoTrading'

export function useAutoTradingStatus() {
  return useQuery<AutoTradingStatus>({
    queryKey: queryKeys.autoTradingStatus,
    queryFn: () => autoTradingService.status(),
    staleTime: 10_000,
  })
}

function invalidateAutoTrading(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.autoTradingStatus })
  void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard })
  void queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus })
}

export function useEnableAutoTrading() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ accountId, confirm, phrase }: { accountId: string; confirm: boolean; phrase?: string }) =>
      autoTradingService.enable(accountId, confirm, phrase),
    onSuccess: () => invalidateAutoTrading(queryClient),
  })
}

export function useDisableAutoTrading() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (accountId: string) => autoTradingService.disable(accountId),
    onSuccess: () => invalidateAutoTrading(queryClient),
  })
}

export function useUpdateAutoTradingPolicy() {
  const queryClient = useQueryClient()
  return useMutation<AutoTradingPolicy, Error, { accountId: string; patch: Partial<AutoTradingPolicy> }>({
    mutationFn: ({ accountId, patch }) => autoTradingService.updatePolicy(accountId, patch),
    onSuccess: () => invalidateAutoTrading(queryClient),
  })
}

export function useBrokerConnections() {
  return useQuery<BrokerConnection[]>({
    queryKey: queryKeys.brokerConnections,
    queryFn: () => brokersService.list(),
    staleTime: 20_000,
  })
}

export function useCreateBrokerConnection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: BrokerConnectionCreateInput) => brokersService.create(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.brokerConnections })
      void queryClient.invalidateQueries({ queryKey: queryKeys.autoTradingStatus })
    },
  })
}

export function useTestBrokerConnection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => brokersService.test(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.brokerConnections }),
  })
}

export function useUpdateBrokerConnection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Record<string, unknown> }) =>
      brokersService.update(id, input),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.brokerConnections }),
  })
}

export function useDeleteBrokerConnection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => brokersService.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.brokerConnections })
      void queryClient.invalidateQueries({ queryKey: queryKeys.autoTradingStatus })
    },
  })
}

export function useActivateBrokerConnection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => brokersService.activate(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.brokerConnections }),
  })
}
