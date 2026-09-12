import { storeToRefs } from 'pinia'
import { websocket } from '~/services/websocket'
import type { AnyTradingEvent } from '~/types/websocket'
import { useWebSocketStore } from '~/stores/websocket'

/**
 * Realtime connection status and subscriptions.
 *
 * Always uses the shared singleton socket — components must never construct
 * their own WebSocket.
 */
export function useWebSocket() {
  const store = useWebSocketStore()
  if (import.meta.client) store.bind()

  const { status, lastConnectedAt, attempts, lastError, recentEvents, isConnected } =
    storeToRefs(store)

  function onEvent(handler: (event: AnyTradingEvent) => void): () => void {
    return websocket.onEvent(handler)
  }

  return {
    status,
    lastConnectedAt,
    attempts,
    lastError,
    recentEvents,
    isConnected,
    onEvent,
    connect: (token?: string | null) => store.connect(token),
    disconnect: () => store.disconnect(),
  }
}
