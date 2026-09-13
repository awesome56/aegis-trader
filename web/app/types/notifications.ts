import type { ISODateString } from './api'

export type NotificationCategory =
  | 'TRADING'
  | 'RISK'
  | 'SYSTEM'
  | 'BROKER'
  | 'MARKET'
  | 'PORTFOLIO'

export type NotificationSeverity = 'INFO' | 'WARNING' | 'CRITICAL'

/** Persistent notification returned by the backend notification centre. */
export interface Notification {
  id: string
  category: string
  severity: NotificationSeverity
  title: string
  message: string
  is_read: boolean
  read_at: ISODateString | null
  payload: Record<string, unknown> | null
  created_at: ISODateString
  /** Resource link derived from structured payload metadata (never parsed text). */
  link?: string
}

export interface NotificationPage {
  items: Notification[]
  total: number
  page: number
  pageSize: number
}

/** Ephemeral, client-side notification used by the realtime toast feed. */
export interface AppNotification {
  id: string
  category: NotificationCategory
  severity: NotificationSeverity
  title: string
  message: string
  created_at: ISODateString
  read: boolean
  to?: string
}
