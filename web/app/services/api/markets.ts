import type { AssetDetail, CandleSeries, CandleTimeframe, MarketOverview, Quote, WatchlistItem } from '~/types/market'
import { api } from './client'
import { isMockEnabled } from './config'
import {
  toAssetDetail,
  toAssetSummary,
  toCandleSeries,
  toMarketOverview,
  toQuote,
  toWatchlistSearch,
} from './adapters'
import type {
  RawAssetSearch,
  RawCandleSeries,
  RawMarketOverview,
  RawQuote,
} from './adapters/raw'
import { mockAsset, mockCandles, mockMarkets, mockQuote } from '~/mocks'

const BACKEND_TIMEFRAME: Record<CandleTimeframe, string> = {
  '1m': '1m',
  '5m': '5m',
  '15m': '15m',
  '1H': '1h',
  '4H': '4h',
  '1D': '1d',
  '1W': '1w',
}

export const marketsService = {
  overview: async (): Promise<MarketOverview> => {
    if (isMockEnabled()) return mockMarkets()
    return toMarketOverview(await api.get<RawMarketOverview>('/markets/overview'))
  },
  search: async (query: string): Promise<WatchlistItem[]> => {
    if (isMockEnabled()) {
      const term = query.trim().toUpperCase()
      return mockMarkets().items.filter((item) => item.symbol.includes(term))
    }
    return toWatchlistSearch(
      await api.get<RawAssetSearch[]>('/markets/search', { query: { q: query } }),
    )
  },
  asset: async (symbol: string): Promise<AssetDetail> => {
    if (isMockEnabled()) return mockAsset(symbol)
    const [results, rawQuote] = await Promise.all([
      api.get<RawAssetSearch[]>('/markets/search', { query: { q: symbol, limit: 5 } }),
      api.get<RawQuote>(`/markets/${encodeURIComponent(symbol)}/quote`),
    ])
    const match = results.find((row) => row.symbol.toUpperCase() === symbol.toUpperCase()) ?? results[0]
    if (!match) throw new Error(`Asset ${symbol} not found`)
    return toAssetDetail(toAssetSummary(match), toQuote(rawQuote))
  },
  quote: async (symbol: string): Promise<Quote> => {
    if (isMockEnabled()) return mockQuote(symbol)
    return toQuote(await api.get<RawQuote>(`/markets/${encodeURIComponent(symbol)}/quote`))
  },
  candles: async (symbol: string, timeframe: CandleTimeframe): Promise<CandleSeries> => {
    if (isMockEnabled()) return mockCandles(symbol, timeframe)
    return toCandleSeries(
      await api.get<RawCandleSeries>(`/markets/${encodeURIComponent(symbol)}/candles`, {
        query: { timeframe: BACKEND_TIMEFRAME[timeframe] },
      }),
    )
  },
}
