import { useQueryClient } from '@tanstack/vue-query'
import { applyEventToCache, websocket } from '~/services/websocket'
import { useNotificationsStore } from '~/stores/notifications'
import { useWebSocketStore } from '~/stores/websocket'

/**
 * Wires the single WebSocket stream into (a) targeted TanStack Query cache
 * updates and (b) the notification centre. Call `start()` once from the app
 * shell. Idempotent.
 */
export function useRealtime() {
  const queryClient = useQueryClient()
  const notifications = useNotificationsStore()
  const wsStore = useWebSocketStore()

  let started = false
  let unsubscribe: (() => void) | null = null

  function start(): void {
    if (started || !import.meta.client) return
    started = true
    wsStore.bind()
    unsubscribe = websocket.onEvent((event) => {
      applyEventToCache(queryClient, event)
      notifications.ingestEvent(event)
    })
  }

  function stop(): void {
    unsubscribe?.()
    unsubscribe = null
    started = false
  }

  return { start, stop }
}
