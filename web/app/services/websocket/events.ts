import type { AnyTradingEvent, WebSocketEnvelope } from '~/types/websocket'
import { WS_EVENTS } from '~/types/websocket'

const KNOWN_EVENTS: ReadonlySet<string> = new Set(Object.values(WS_EVENTS))

export function isKnownEvent(name: string): boolean {
  return KNOWN_EVENTS.has(name)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/**
 * Parse a raw WebSocket frame into a typed event.
 * Returns null for malformed frames (never throws, never drops silently at the
 * caller — the caller logs unknown events).
 */
export function parseTradingEvent(raw: unknown): AnyTradingEvent | null {
  let payload: unknown = raw

  if (typeof raw === 'string') {
    try {
      payload = JSON.parse(raw)
    } catch {
      return null
    }
  }

  if (!isRecord(payload)) return null

  const event = payload.event
  if (typeof event !== 'string' || event.length === 0) return null

  const timestamp = typeof payload.timestamp === 'string' ? payload.timestamp : new Date().toISOString()
  const data = isRecord(payload.data) ? payload.data : {}

  return { event, timestamp, data } as AnyTradingEvent
}

/** Serialise an envelope (used by tests and future client-side pings). */
export function buildEnvelope<T>(event: string, data: T, timestamp?: string): WebSocketEnvelope<T> {
  return { event, data, timestamp: timestamp ?? new Date().toISOString() }
}
