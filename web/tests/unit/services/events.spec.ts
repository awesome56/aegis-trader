import { describe, expect, it } from 'vitest'
import { buildEnvelope, isKnownEvent, parseTradingEvent } from '~/services/websocket/events'
import { WS_EVENTS } from '~/types/websocket'

describe('websocket event parsing', () => {
  it('parses a JSON string envelope', () => {
    const raw = JSON.stringify({
      event: 'order.filled',
      timestamp: '2026-01-01T00:00:00.000Z',
      data: { order_id: '1', symbol: 'NVDA', status: 'FILLED' },
    })
    const event = parseTradingEvent(raw)
    expect(event?.event).toBe('order.filled')
    expect(event?.data.symbol).toBe('NVDA')
  })

  it('parses an already-decoded object', () => {
    const event = parseTradingEvent({ event: 'risk.warning', timestamp: 't', data: {} })
    expect(event?.event).toBe('risk.warning')
  })

  it('returns null for malformed frames', () => {
    expect(parseTradingEvent('{not json')).toBeNull()
    expect(parseTradingEvent('123')).toBeNull()
    expect(parseTradingEvent(null)).toBeNull()
  })

  it('rejects envelopes without an event name', () => {
    expect(parseTradingEvent({ data: {} })).toBeNull()
    expect(parseTradingEvent({ event: '' })).toBeNull()
  })

  it('defaults a missing timestamp rather than throwing', () => {
    const event = parseTradingEvent({ event: 'agent.completed', data: {} })
    expect(event?.timestamp).toBeTruthy()
    expect(event?.data).toEqual({})
  })

  it('recognises known event names', () => {
    expect(isKnownEvent(WS_EVENTS.orderFilled)).toBe(true)
    expect(isKnownEvent('totally.unknown')).toBe(false)
  })

  it('builds envelopes', () => {
    const envelope = buildEnvelope('quote.updated', { symbol: 'AAPL' }, '2026-01-01T00:00:00.000Z')
    expect(envelope.timestamp).toBe('2026-01-01T00:00:00.000Z')
    expect(envelope.event).toBe('quote.updated')
  })
})
