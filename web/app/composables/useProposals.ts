import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { proposalsService } from '~/services/api/proposals'
import type {
  ExecutionOutcome,
  ProposalCreateInput,
  ProposalDetail,
  TradeProposal,
} from '~/types/agent'
import type { PageParams, Paginated } from '~/types/api'

export function useProposals(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<TradeProposal>>({
    queryKey: computed(() => queryKeys.proposals(toValue(params))),
    queryFn: () => proposalsService.list(toValue(params)),
    staleTime: 10_000,
  })
}

export function useProposalDetail(id: MaybeRefOrGetter<string>) {
  return useQuery<ProposalDetail>({
    queryKey: computed(() => queryKeys.proposal(toValue(id))),
    queryFn: () => proposalsService.get(toValue(id)),
    enabled: computed(() => Boolean(toValue(id))),
    staleTime: 5_000,
  })
}

export function useCreateProposal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: ProposalCreateInput) => proposalsService.create(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.proposalsRoot })
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard })
      void queryClient.invalidateQueries({ queryKey: queryKeys.activityRoot })
    },
  })
}

export function useEvaluateProposal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => proposalsService.evaluate(id),
    onSuccess: (_result, id) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.proposal(id) })
      void queryClient.invalidateQueries({ queryKey: queryKeys.proposalsRoot })
      void queryClient.invalidateQueries({ queryKey: queryKeys.riskStatus })
      void queryClient.invalidateQueries({ queryKey: ['risk', 'events'] })
      void queryClient.invalidateQueries({ queryKey: queryKeys.activityRoot })
    },
  })
}

export function useExecuteProposal() {
  const queryClient = useQueryClient()
  return useMutation<ExecutionOutcome, Error, string>({
    mutationFn: (id: string) => proposalsService.execute(id),
    onSuccess: (_result, id) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.proposal(id) })
      void queryClient.invalidateQueries({ queryKey: queryKeys.proposalsRoot })
      void queryClient.invalidateQueries({ queryKey: queryKeys.ordersRoot })
      void queryClient.invalidateQueries({ queryKey: queryKeys.portfolio })
      void queryClient.invalidateQueries({ queryKey: queryKeys.positionsRoot })
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard })
      void queryClient.invalidateQueries({ queryKey: queryKeys.activityRoot })
    },
  })
}

export function useCancelProposal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => proposalsService.cancel(id),
    onSuccess: (_result, id) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.proposal(id) })
      void queryClient.invalidateQueries({ queryKey: queryKeys.proposalsRoot })
      void queryClient.invalidateQueries({ queryKey: queryKeys.activityRoot })
    },
  })
}
