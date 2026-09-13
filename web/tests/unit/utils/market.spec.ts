import { describe, expect, it } from 'vitest'
import type { WatchlistItem } from '~/types/market'
import { regimeBreakdown, topMovers } from '~/utils/market'

function item(symbol: string, change: string | null, regime: WatchlistItem['market_regime']): WatchlistItem {
  return {
    symbol, name: null, price: '100', bid: null, ask: null, previous_close: null,
    change: null, change_pct: change, day_high: null, day_low: null, volume: null,
    signal: null, market_regime: regime, confidence: null, strategy: null,
    quote_time: null, age_seconds: 1, is_stale: false,
  }
}

describe('market helpers', () => {
  it('ranks gainers and losers by change percent', () => {
    const items = [item('A', '2', 'BULLISH'), item('B', '-3', 'BEARISH'), item('C', '1', 'SIDEWAYS'), item('D', '5', 'BULLISH'), item('E', null, null)]
    const { gainers, losers } = topMovers(items, 2)
    expect(gainers.map((i) => i.symbol)).toEqual(['D', 'A'])
    expect(losers.map((i) => i.symbol)).toEqual(['B'])
  })

  it('counts regimes', () => {
    const items = [item('A', '1', 'BULLISH'), item('B', '1', 'BULLISH'), item('C', '0', 'SIDEWAYS'), item('D', '0', null)]
    expect(regimeBreakdown(items)).toEqual([
      { regime: 'BULLISH', count: 2 },
      { regime: 'SIDEWAYS', count: 1 },
    ])
  })
})
