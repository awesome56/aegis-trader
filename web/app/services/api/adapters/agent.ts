import type { AgentStatus } from '~/types/agent'

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
