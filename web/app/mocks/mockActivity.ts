import type { ActivityEvent } from '~/types/activity'
import { mockIso } from './helpers'

export function mockActivity(): ActivityEvent[] {
  const base: Omit<ActivityEvent, 'id' | 'occurred_at'>[] = [
    { component: 'STRATEGY', event_type: 'strategy.signal', severity: 'INFO', message: 'Momentum signal detected on NVDA', symbol: 'NVDA', correlation_id: 'corr-1', data: null },
    { component: 'AGENT', event_type: 'agent.started', severity: 'INFO', message: 'Agent analysis run started', symbol: null, correlation_id: 'corr-1', data: null },
    { component: 'AGENT', event_type: 'agent.completed', severity: 'INFO', message: 'Agent analysis completed for 4 symbols', symbol: null, correlation_id: 'corr-1', data: null },
    { component: 'AGENT', event_type: 'proposal.created', severity: 'INFO', message: 'BUY proposal generated for NVDA', symbol: 'NVDA', correlation_id: 'corr-1', data: null },
    { component: 'RISK', event_type: 'risk.approved', severity: 'INFO', message: 'Proposal approved by risk engine', symbol: 'NVDA', correlation_id: 'corr-1', data: null },
    { component: 'ORDER', event_type: 'order.submitted', severity: 'INFO', message: 'Order submitted to paper broker', symbol: 'NVDA', correlation_id: 'corr-1', data: null },
    { component: 'BROKER', event_type: 'order.filled', severity: 'INFO', message: 'Order filled at 126.52', symbol: 'NVDA', correlation_id: 'corr-1', data: null },
    { component: 'RISK', event_type: 'risk.warning', severity: 'WARNING', message: 'Technology sector exposure near limit', symbol: null, correlation_id: null, data: null },
    { component: 'RISK', event_type: 'proposal.rejected', severity: 'WARNING', message: 'TSLA proposal rejected: sector concentration', symbol: 'TSLA', correlation_id: 'corr-2', data: null },
    { component: 'SYSTEM', event_type: 'broker.connected', severity: 'INFO', message: 'Paper broker connected', symbol: null, correlation_id: null, data: null },
  ]
  return base.map((event, index) => ({
    ...event,
    id: `act-${index + 1}`,
    occurred_at: mockIso(0, index),
  }))
}
