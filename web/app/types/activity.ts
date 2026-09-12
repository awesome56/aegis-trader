import type { ISODateString } from './api'

export type ActivityComponent =
  | 'AGENT'
  | 'STRATEGY'
  | 'RISK'
  | 'ORDER'
  | 'BROKER'
  | 'PORTFOLIO'
  | 'SYSTEM'

export type ActivitySeverity = 'INFO' | 'WARNING' | 'CRITICAL'

export interface ActivityEvent {
  id: string
  component: ActivityComponent
  event_type: string
  severity: ActivitySeverity
  message: string
  symbol: string | null
  correlation_id: string | null
  data: Record<string, unknown> | null
  occurred_at: ISODateString
}
