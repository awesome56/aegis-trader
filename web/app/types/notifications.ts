import type { ISODateString } from './api'

export type NotificationCategory =
  | 'TRADING'
  | 'RISK'
  | 'AGENT'
  | 'SYSTEM'
  | 'BROKER'
  | 'MARKET'

export type NotificationSeverity = 'INFO' | 'WARNING' | 'CRITICAL'

export interface AppNotification {
  id: string
  category: NotificationCategory
  severity: NotificationSeverity
  title: string
  message: string
  created_at: ISODateString
  read: boolean
  /** Optional in-app destination, e.g. /trades/123. */
  to?: string
}
