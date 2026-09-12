import { defineStore } from 'pinia'
import type { AnyTradingEvent } from '~/types/websocket'
import { websocket } from '~/services/websocket'
import type { SocketStatus } from '~/services/websocket'

const MAX_RECENT_EVENTS = 100

/**
 * WebSocket connectivity state. Mirrors the singleton manager and keeps a small
 * ring buffer of recent events for live UI (never authoritative data).
 */
export const useWebSocketStore = defineStore('websocket', () => {
  const status = ref<SocketStatus>('disconnected')
  const lastConnectedAt = ref<string | null>(null)
  const attempts = ref(0)
  const lastError = ref<string | null>(null)
  const recentEvents = ref<AnyTradingEvent[]>([])

  let unsubscribeState: (() => void) | null = null

  const isConnected = computed(() => status.value === 'connected')

  /** Bind the store to the shared manager. Idempotent. */
  function bind(): void {
    if (unsubscribeState) return
    unsubscribeState = websocket.onState((state) => {
      status.value = state.status
      lastConnectedAt.value = state.lastConnectedAt
      attempts.value = state.attempts
      lastError.value = state.lastError
    })
    websocket.onEvent((event) => {
      recentEvents.value = [event, ...recentEvents.value].slice(0, MAX_RECENT_EVENTS)
    })
  }

  function connect(token?: string | null): void {
    bind()
    websocket.connect(token)
  }

  function disconnect(): void {
    websocket.disconnect()
  }

  function reset(): void {
    recentEvents.value = []
  }

  return {
    status,
    lastConnectedAt,
    attempts,
    lastError,
    recentEvents,
    isConnected,
    bind,
    connect,
    disconnect,
    reset,
  }
})
