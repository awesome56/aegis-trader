import type {
  AgentDecisionRecord,
  AgentEvidenceRecord,
  AgentMode,
  AgentRun,
  AgentRunStatus,
  AgentRuntimeStatus,
  AgentStatus,
  OrderAction,
} from '~/types/agent'
import type { MarketRegime } from '~/types/market'
import type { Paginated } from '~/types/api'
import { iso, isoOrNull, num } from './common'
import type {
  RawAgentDecision,
  RawAgentDecisionPage,
  RawAgentRun,
  RawAgentRunPage,
  RawAgentStatus,
} from './raw'

export function toAgentRun(raw: RawAgentRun): AgentRun {
  return {
    id: raw.id,
    status: raw.status as AgentRunStatus,
    provider: raw.provider,
    model: raw.model,
    mode: raw.mode as AgentMode,
    symbols: raw.symbols ?? [],
    prompt: raw.prompt,
    error: raw.error,
    latency_ms: raw.latency_ms,
    tokens_used: raw.tokens_used,
    usage: raw.usage,
    proposal_id: raw.proposal_id,
    started_at: isoOrNull(raw.started_at),
    completed_at: isoOrNull(raw.completed_at),
    created_at: iso(raw.created_at),
  }
}

export function toAgentRuntimeStatus(raw: RawAgentStatus): AgentRuntimeStatus {
  return {
    enabled: raw.enabled,
    default_mode: raw.default_mode,
    provider: raw.provider,
    model: raw.model,
    provider_status: raw.provider_status,
    provider_config_id: raw.provider_config_id,
    running: raw.running,
    runs_today: raw.runs_today,
    recent_failures: raw.recent_failures,
    last_run: raw.last_run ? toAgentRun(raw.last_run as unknown as RawAgentRun) : null,
  }
}

export function toAgentRunPage(raw: RawAgentRunPage): Paginated<AgentRun> {
  return {
    items: raw.items.map(toAgentRun),
    total: raw.total,
    page: raw.page,
    pageSize: raw.page_size,
  }
}

function toEvidence(raw: NonNullable<RawAgentDecision['evidence']>[number]): AgentEvidenceRecord {
  return {
    type: raw.type,
    source: raw.source,
    direction: raw.direction ?? null,
    confidence: raw.confidence ?? null,
    data: raw.data ?? {},
  }
}

export function toAgentDecisionRecord(raw: RawAgentDecision): AgentDecisionRecord {
  return {
    id: raw.id,
    agent_run_id: raw.agent_run_id,
    symbol: raw.symbol,
    action: raw.action as OrderAction,
    confidence: num(raw.confidence),
    reasoning_summary: raw.reasoning_summary,
    evidence: (raw.evidence ?? []).map(toEvidence),
    concerns: raw.concerns ?? [],
    proposal_recommended: raw.proposal_recommended,
    market_regime: (raw.market_regime as MarketRegime | null) ?? null,
    strategy_signal_ids: raw.strategy_signal_ids ?? [],
    proposal_id: raw.proposal_id,
    created_at: iso(raw.created_at),
  }
}

export function toAgentDecisionPage(raw: RawAgentDecisionPage): Paginated<AgentDecisionRecord> {
  return {
    items: raw.items.map(toAgentDecisionRecord),
    total: raw.total,
    page: raw.page,
    pageSize: raw.page_size,
  }
}


/** Disabled placeholder used by the dashboard until the agent is configured. */
export function toAgentStatusDisabled(): AgentStatus {
  return {
    enabled: false,
    running: false,
    last_analysis_at: null,
    next_run_at: null,
    symbols_under_analysis: [],
    decisions_today: 0,
    proposals_today: 0,
    approved_today: 0,
    rejected_today: 0,
    error_count_today: 0,
    last_error: null,
  }
}
