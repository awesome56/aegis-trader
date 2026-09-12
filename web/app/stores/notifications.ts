import { defineStore } from 'pinia'
import type { AppNotification, NotificationCategory, NotificationSeverity } from '~/types/notifications'
import type { AnyTradingEvent } from '~/types/websocket'
import { WS_EVENTS } from '~/types/websocket'

interface NotificationInput {
  category: NotificationCategory
  severity: NotificationSeverity
  title: string
  message: string
  to?: string
}

const MAX_NOTIFICATIONS = 200

function createId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `ntf-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

/** Client-side notification centre fed by WebSocket events. */
export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<AppNotification[]>([])

  const unreadCount = computed(() => items.value.filter((item) => !item.read).length)

  function push(input: NotificationInput): void {
    items.value = [
      {
        id: createId(),
        created_at: new Date().toISOString(),
        read: false,
        ...input,
      },
      ...items.value,
    ].slice(0, MAX_NOTIFICATIONS)
  }

  function markRead(id: string): void {
    items.value = items.value.map((item) => (item.id === id ? { ...item, read: true } : item))
  }

  function markAllRead(): void {
    items.value = items.value.map((item) => ({ ...item, read: true }))
  }

  function remove(id: string): void {
    items.value = items.value.filter((item) => item.id !== id)
  }

  function clear(): void {
    items.value = []
  }

  /** Translate a realtime event into a user-facing notification. */
  function ingestEvent(event: AnyTradingEvent): void {
    const label = 'symbol' in event.data ? String(event.data.symbol ?? '') : ''
    switch (event.event) {
      case WS_EVENTS.orderFilled:
        push({
          category: 'TRADING',
          severity: 'INFO',
          title: 'Order filled',
          message: `${label} order filled`.trim(),
          to: '/orders',
        })
        break
      case WS_EVENTS.orderFailed:
        push({
          category: 'TRADING',
          severity: 'WARNING',
          title: 'Order failed',
          message: `${label} order failed`.trim(),
          to: '/orders',
        })
        break
      case WS_EVENTS.tradeCompleted:
        push({
          category: 'TRADING',
          severity: 'INFO',
          title: 'Trade completed',
          message: `${label} trade closed`.trim(),
          to: '/trades',
        })
        break
      case WS_EVENTS.proposalCreated:
        push({
          category: 'AGENT',
          severity: 'INFO',
          title: 'New trade proposal',
          message: `${label} proposal generated`.trim(),
          to: '/agent/proposals',
        })
        break
      case WS_EVENTS.proposalRejected:
        push({
          category: 'RISK',
          severity: 'WARNING',
          title: 'Proposal rejected',
          message: `${label} proposal rejected by risk engine`.trim(),
          to: '/agent/proposals',
        })
        break
      case WS_EVENTS.riskWarning:
        push({
          category: 'RISK',
          severity: 'WARNING',
          title: 'Risk warning',
          message: String(event.data.message ?? 'Risk limit approaching'),
          to: '/risk',
        })
        break
      case WS_EVENTS.riskCritical:
        push({
          category: 'RISK',
          severity: 'CRITICAL',
          title: 'Critical risk alert',
          message: String(event.data.message ?? 'Risk limit exceeded'),
          to: '/risk',
        })
        break
      case WS_EVENTS.brokerDisconnected:
        push({
          category: 'BROKER',
          severity: 'CRITICAL',
          title: 'Broker disconnected',
          message: 'The broker connection was lost.',
          to: '/settings',
        })
        break
      case WS_EVENTS.systemStatusChanged:
        push({
          category: 'SYSTEM',
          severity: 'WARNING',
          title: 'Trading status changed',
          message: `System is now ${String(event.data.kill_switch_state ?? 'updated')}.`,
          to: '/settings',
        })
        break
      default:
        break
    }
  }

  return {
    items,
    unreadCount,
    push,
    markRead,
    markAllRead,
    remove,
    clear,
    ingestEvent,
  }
})
