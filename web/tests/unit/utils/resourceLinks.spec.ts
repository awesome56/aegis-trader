import { describe, expect, it } from 'vitest'
import { resourceLinkFromPayload } from '~/utils/resourceLinks'

describe('resourceLinkFromPayload', () => {
  it('links structured identifiers to in-app resources', () => {
    expect(resourceLinkFromPayload({ proposal_id: 'pr-1' })).toBe('/agent/proposals/pr-1')
    expect(resourceLinkFromPayload({ order_id: 'o-1' })).toBe('/orders/o-1')
    expect(resourceLinkFromPayload({ trade_id: 't-1' })).toBe('/trades/t-1')
    expect(resourceLinkFromPayload({ position_id: 'pos-1' })).toBe('/positions/pos-1')
    expect(resourceLinkFromPayload({ strategy_id: 's-1' })).toBe('/strategies/s-1')
  })

  it('returns undefined when no structured identifier exists', () => {
    expect(resourceLinkFromPayload(null)).toBeUndefined()
    expect(resourceLinkFromPayload({ symbol: 'AAPL', note: 'no ids' })).toBeUndefined()
    expect(resourceLinkFromPayload({ proposal_id: 123 })).toBeUndefined()
  })
})
