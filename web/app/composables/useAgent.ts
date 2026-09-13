import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { agentService } from '~/services/api/agent'
import type { AgentDecisionRecord, AgentRun, AgentRuntimeStatus, AnalyzeInput } from '~/types/agent'
import type { PageParams, Paginated } from '~/types/api'

export function useAgentStatus() {
  return useQuery<AgentRuntimeStatus>({
    queryKey: queryKeys.agentStatus,
    queryFn: () => agentService.status(),
    staleTime: 15_000,
  })
}

export function useAgentRuns(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<AgentRun>>({
    queryKey: computed(() => queryKeys.agentRuns(toValue(params))),
    queryFn: () => agentService.runs(toValue(params)),
    staleTime: 10_000,
  })
}

export function useAgentRun(id: MaybeRefOrGetter<string>) {
  return useQuery<AgentRun>({
    queryKey: computed(() => queryKeys.agentRun(toValue(id))),
    queryFn: () => agentService.run(toValue(id)),
    enabled: computed(() => Boolean(toValue(id))),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'PENDING' || status === 'RUNNING' ? 2500 : false
    },
  })
}

export function useAgentDecisions(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<AgentDecisionRecord>>({
    queryKey: computed(() => queryKeys.agentDecisions(toValue(params))),
    queryFn: () => agentService.decisions(toValue(params)),
    staleTime: 15_000,
  })
}

export function useAgentDecision(id: MaybeRefOrGetter<string>) {
  return useQuery<AgentDecisionRecord>({
    queryKey: computed(() => queryKeys.agentDecision(toValue(id))),
    queryFn: () => agentService.decision(toValue(id)),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

/** Create + run an analysis. The agent never executes trades. */
export function useCreateAgentRun() {
  const queryClient = useQueryClient()
  return useMutation<AgentRun, Error, AnalyzeInput>({
    mutationFn: (input: AnalyzeInput) => agentService.createRun(input),
    onSuccess: (run) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.agentRunsRoot })
      void queryClient.invalidateQueries({ queryKey: queryKeys.agentDecisionsRoot })
      void queryClient.invalidateQueries({ queryKey: queryKeys.agentStatus })
      void queryClient.invalidateQueries({ queryKey: queryKeys.agentRun(run.id) })
      if (run.proposal_id) {
        void queryClient.invalidateQueries({ queryKey: queryKeys.proposalsRoot })
      }
    },
  })
}
