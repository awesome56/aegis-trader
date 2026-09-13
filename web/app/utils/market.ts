import type { MarketRegime, WatchlistItem } from '~/types/market'

/** Presentational helpers for the markets watchlist (client-side sorting only). */

export function topMovers(
  items: WatchlistItem[],
  count = 3,
): { gainers: WatchlistItem[]; losers: WatchlistItem[] } {
  const ranked = items
    .filter((item) => item.change_pct !== null)
    .slice()
    .sort((a, b) => Number(b.change_pct) - Number(a.change_pct))
  return {
    gainers: ranked.slice(0, count),
    losers: ranked.slice(-count).reverse().filter((item) => Number(item.change_pct) < 0),
  }
}

export function regimeBreakdown(
  items: WatchlistItem[],
): { regime: MarketRegime; count: number }[] {
  const counts = new Map<MarketRegime, number>()
  for (const item of items) {
    if (!item.market_regime) continue
    counts.set(item.market_regime, (counts.get(item.market_regime) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([regime, count]) => ({ regime, count }))
    .sort((a, b) => b.count - a.count)
}
