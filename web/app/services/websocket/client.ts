import type { AnyTradingEvent } from '~/types/websocket'
import { apiConfig } from '../api/config'
import { parseTradingEvent } from './events'

export type SocketStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting'

export interface WebSocketState {
  status: SocketStatus
  lastConnectedAt: string | null
  attempts: number
  lastError: string | null
}

type EventListener = (event: AnyTradingEvent) => void
type StateListener = (state: WebSocketState) => void

const MAX_BACKOFF_MS = 30_000
const BASE_BACKOFF_MS = 1_000
const DEDUPE_LIMIT = 500
const WS_PATH = '/ws'

/**
 * Central, single-instance WebSocket connection.
 *
 * Components never open their own sockets: they subscribe here via the
 * `useWebSocket` composable. Handles automatic reconnect with exponential
 * backoff + jitter, connection state, and duplicate suppression.
 */
export class WebSocketManager {
  private socket: WebSocket | null = null
  private eventListeners = new Set<EventListener>()
  private stateListeners = new Set<StateListener>()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private manuallyClosed = false
  private seen = new Set<string>()
  private seenOrder: string[] = []
  private token: string | null = null

  private current: WebSocketState = {
    status: 'disconnected',
    lastConnectedAt: null,
    attempts: 0,
    lastError: null,
  }

  get state(): WebSocketState {
    return { ...this.current }
  }

  connect(token?: string | null): void {
    if (token !== undefined) this.token = token
    if (this.socket && this.current.status === 'connected') return

    this.manuallyClosed = false
    this.open()
  }

  private buildUrl(): string {
    const base = apiConfig().wsUrl.replace(/\/$/, '')
    const query = this.token ? `?token=${encodeURIComponent(this.token)}` : ''
    return `${base}${WS_PATH}${query}`
  }

  private open(): void {
    this.setState({
      status: this.current.attempts > 0 ? 'reconnecting' : 'connecting',
      lastError: null,
    })

    try {
      const socket = new WebSocket(this.buildUrl())
      this.socket = socket

      socket.onopen = () => {
        this.current.attempts = 0
        this.setState({ status: 'connected', lastConnectedAt: new Date().toISOString() })
      }

      socket.onmessage = (message) => {
        const event = parseTradingEvent(message.data)
        if (!event) return
        if (this.isDuplicate(event)) return
        for (const listener of this.eventListeners) listener(event)
      }

      socket.onclose = () => {
        this.socket = null
        if (this.manuallyClosed) {
          this.setState({ status: 'disconnected' })
          return
        }
        this.scheduleReconnect()
      }

      socket.onerror = () => {
        this.setState({ lastError: 'WebSocket error' })
      }
    } catch (error) {
      this.setState({ lastError: error instanceof Error ? error.message : 'WebSocket failure' })
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return
    const attempt = this.current.attempts + 1
    const backoff = Math.min(MAX_BACKOFF_MS, BASE_BACKOFF_MS * 2 ** (attempt - 1))
    const jitter = Math.random() * 0.25 * backoff
    this.setState({ status: 'reconnecting', attempts: attempt })

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      if (!this.manuallyClosed) this.open()
    }, backoff + jitter)
  }

  private isDuplicate(event: AnyTradingEvent): boolean {
    const key = `${event.event}|${event.timestamp}|${JSON.stringify(event.data)}`
    if (this.seen.has(key)) return true
    this.seen.add(key)
    this.seenOrder.push(key)
    if (this.seenOrder.length > DEDUPE_LIMIT) {
      const oldest = this.seenOrder.shift()
      if (oldest) this.seen.delete(oldest)
    }
    return false
  }

  disconnect(): void {
    this.manuallyClosed = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.socket?.close()
    this.socket = null
    this.setState({ status: 'disconnected', attempts: 0 })
  }

  onEvent(listener: EventListener): () => void {
    this.eventListeners.add(listener)
    return () => this.eventListeners.delete(listener)
  }

  onState(listener: StateListener): () => void {
    this.stateListeners.add(listener)
    listener(this.state)
    return () => this.stateListeners.delete(listener)
  }

  private setState(patch: Partial<WebSocketState>): void {
    this.current = { ...this.current, ...patch }
    for (const listener of this.stateListeners) listener(this.state)
  }
}

/** Shared singleton — the one and only browser socket. */
export const websocket = new WebSocketManager()
