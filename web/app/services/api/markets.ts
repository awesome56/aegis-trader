import type { AssetDetail, CandleSeries, CandleTimeframe, MarketOverview, Quote, WatchlistItem } from '~/types/market'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockAsset, mockCandles, mockMarkets, mockQuote } from '~/mocks'

/**
 * BACKEND REQUIREMENT (not yet implemented):
 *   GET /markets
 *   GET /markets/search?q=
 *   GET /markets/{symbol}
 *   GET /markets/{symbol}/candles?timeframe=
 *   GET /markets/{symbol}/quote
 */
export const marketsService = {
  overview: async (): Promise<MarketOverview> => {
    if (isMockEnabled()) return mockMarkets()
    return api.get<MarketOverview>('/markets')
  },
  search: async (query: string): Promise<WatchlistItem[]> => {
    if (isMockEnabled()) {
      const term = query.trim().toUpperCase()
      return mockMarkets().items.filter((item) => item.symbol.includes(term))
    }
    return api.get<WatchlistItem[]>('/markets/search', { query: { q: query } })
  },
  asset: async (symbol: string): Promise<AssetDetail> => {
    if (isMockEnabled()) return mockAsset(symbol)
    return api.get<AssetDetail>(`/markets/${encodeURIComponent(symbol)}`)
  },
  quote: async (symbol: string): Promise<Quote> => {
    if (isMockEnabled()) return mockQuote(symbol)
    return api.get<Quote>(`/markets/${encodeURIComponent(symbol)}/quote`)
  },
  candles: async (symbol: string, timeframe: CandleTimeframe): Promise<CandleSeries> => {
    if (isMockEnabled()) return mockCandles(symbol, timeframe)
    return api.get<CandleSeries>(`/markets/${encodeURIComponent(symbol)}/candles`, {
      query: { timeframe },
    })
  },
}
