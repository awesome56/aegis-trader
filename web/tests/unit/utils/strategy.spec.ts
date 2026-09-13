import { describe, expect, it } from 'vitest'
import { signalDirectionToSide } from '~/utils/strategy'

describe('signalDirectionToSide', () => {
  it('maps LONG to BUY and SHORT to SELL', () => {
    expect(signalDirectionToSide('LONG')).toBe('BUY')
    expect(signalDirectionToSide('SHORT')).toBe('SELL')
  })

  it('never maps NEUTRAL to a side', () => {
    expect(signalDirectionToSide('NEUTRAL')).toBeNull()
  })
})
