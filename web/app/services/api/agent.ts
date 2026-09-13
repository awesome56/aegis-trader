import type {
  AgentDecisionRecord,
  AgentRun,
  AgentRuntimeStatus,
  AnalyzeInput,
} from '~/types/agent'
import type { PageParams, Paginated } from '~/types/api'
import { api } from './client'
import { isMockEnabled } from './config'
import {
  toAgentDecisionPage,
  toAgentDecisionRecord,
  toAgentRun,
  toAgentRunPage,
  toAgentRuntimeStatus,
} from './adapters'
import type {
  RawAgentDecision,
  RawAgentDecisionPage,
  RawAgentRun,
  RawAgentRunPage,
  RawAgentStatus,
} from './adapters/raw'

function query(params: PageParams): Record<string, unknown> {
  const page = Number(params.page ?? 1)
  const pageSize = Number(params.pageSize ?? 25)
  return { page, page_size: pageSize }
}

/** TradingAnalysisAgent read/run API. Analysis and proposal creation only — never execution. */
export const agentService = {
  status: async (): Promise<AgentRuntimeStatus> => {
    if (isMockEnabled()) {
      return {
        enabled: false,
        default_mode: 'ANALYSIS_ONLY',
        provider: null,
        model: null,
        provider_status: 'NOT_CONFIGURED',
        provider_config_id: null,
        running: 0,
        runs_today: 0,
        recent_failures: 0,
        last_run: null,
      }
    }
    return toAgentRuntimeStatus(await api.get<RawAgentStatus>('/agent/status'))
  },
  runs: async (params: PageParams = {}): Promise<Paginated<AgentRun>> => {
    if (isMockEnabled()) return { items: [], total: 0, page: 1, pageSize: 0 }
    return toAgentRunPage(await api.get<RawAgentRunPage>('/agent/runs', { query: query(params) }))
  },
  run: async (id: string): Promise<AgentRun> => {
    if (isMockEnabled()) throw new Error('Agent runs are unavailable in mock mode')
    return toAgentRun(await api.get<RawAgentRun>(`/agent/runs/${id}`))
  },
  createRun: async (input: AnalyzeInput): Promise<AgentRun> => {
    if (isMockEnabled()) throw new Error('Agent runs are unavailable in mock mode')
    return toAgentRun(await api.post<RawAgentRun>('/agent/runs', input))
  },
  decisions: async (params: PageParams = {}): Promise<Paginated<AgentDecisionRecord>> => {
    if (isMockEnabled()) return { items: [], total: 0, page: 1, pageSize: 0 }
    return toAgentDecisionPage(
      await api.get<RawAgentDecisionPage>('/agent/decisions', { query: query(params) }),
    )
  },
  decision: async (id: string): Promise<AgentDecisionRecord> => {
    if (isMockEnabled()) throw new Error('Agent decisions are unavailable in mock mode')
    return toAgentDecisionRecord(await api.get<RawAgentDecision>(`/agent/decisions/${id}`))
  },
}
