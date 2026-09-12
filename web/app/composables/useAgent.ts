import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { agentService } from '~/services/api/agent'
import type { PageParams, Paginated } from '~/types/api'
import type { AgentDecision, AgentStatus, ProposalPipeline, TradeProposal } from '~/types/agent'

export function useAgentStatus() {
  return useQuery<AgentStatus>({
    queryKey: queryKeys.agentStatus,
    queryFn: () => agentService.status(),
    staleTime: 15_000,
  })
}

export function useAgentDecisions(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<AgentDecision>>({
    queryKey: computed(() => queryKeys.decisions(toValue(params))),
    queryFn: () => agentService.decisions(toValue(params)),
    staleTime: 15_000,
  })
}

export function useTradeProposals(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<TradeProposal>>({
    queryKey: computed(() => queryKeys.proposals(toValue(params))),
    queryFn: () => agentService.proposals(toValue(params)),
    staleTime: 15_000,
  })
}

export function useProposalPipeline(id: MaybeRefOrGetter<string>) {
  return useQuery<ProposalPipeline>({
    queryKey: computed(() => queryKeys.pipeline(toValue(id))),
    queryFn: () => agentService.pipeline(toValue(id)),
    enabled: computed(() => Boolean(toValue(id))),
  })
}
