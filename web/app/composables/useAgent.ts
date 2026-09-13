import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { agentService } from '~/services/api/agent'
import type { AgentDecision, AgentStatus } from '~/types/agent'
import type { PageParams, Paginated } from '~/types/api'

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
