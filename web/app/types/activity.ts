import type { ISODateString } from './api'

export type ActivitySeverity = 'INFO' | 'WARNING' | 'CRITICAL'

/** A normalized audit/system event. Backend `source`→`component`, `payload`→`data`. */
export interface ActivityEvent {
  id: string
  component: string
  event_type: string
  severity: ActivitySeverity
  message: string
  symbol: string | null
  actor?: string | null
  correlation_id: string | null
  data: Record<string, unknown> | null
  occurred_at: ISODateString
  /** Resource link derived from structured payload metadata. */
  link?: string
}
