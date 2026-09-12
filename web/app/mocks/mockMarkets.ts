import type {
  AssetDetail,
  CandleSeries,
  CandleTimeframe,
  MarketOverview,
  Quote,
  WatchlistItem,
} from '~/types/market'
import { mockSignals } from './mockStrategies'
import { mockIso } from './helpers'

const WATCHLIST: WatchlistItem[] = [
  {
    symbol: 'NVDA',
    name: 'NVIDIA Corporation',
    price: '126.85',
    change_pct: '2.14',
    volume: '41200000',
    signal: 'LONG',
    market_regime: 'BULLISH',
  },
  {
    symbol: 'AAPL',
    name: 'Apple Inc.',
    price: '221.05',
    change_pct: '0.42',
    volume: '28100000',
    signal: 'LONG',
    market_regime: 'BULLISH',
  },
  {
    symbol: 'MSFT',
    name: 'Microsoft Corporation',
    price: '410.55',
    change_pct: '-0.31',
    volume: '19900000',
    signal: 'NEUTRAL',
    market_regime: 'SIDEWAYS',
  },
  {
    symbol: 'TSLA',
    name: 'Tesla, Inc.',
    price: '236.40',
    change_pct: '-1.82',
    volume: '35600000',
    signal: 'SHORT',
    market_regime: 'HIGH_VOLATILITY',
  },
  {
    symbol: 'AMZN',
    name: 'Amazon.com, Inc.',
    price: '188.40',
    change_pct: '1.05',
    volume: '22700000',
    signal: 'NEUTRAL',
    market_regime: 'SIDEWAYS',
  },
]

export function mockMarkets(): MarketOverview {
  return { regime: 'BULLISH', as_of: mockIso(0, 0), items: WATCHLIST.map((item) => ({ ...item })) }
}

export function mockQuote(symbol: string): Quote {
  const item = WATCHLIST.find((entry) => entry.symbol === symbol.toUpperCase()) ?? WATCHLIST[0]!
  const price = Number(item.price ?? 0)
  return {
    symbol: item.symbol,
    price: item.price ?? '0',
    bid: (price - 0.02).toFixed(2),
    ask: (price + 0.02).toFixed(2),
    change: ((price * Number(item.change_pct ?? 0)) / 100).toFixed(2),
    change_pct: item.change_pct ?? '0',
    volume: item.volume,
    day_high: (price * 1.02).toFixed(2),
    day_low: (price * 0.98).toFixed(2),
    market_regime: item.market_regime,
    quote_time: mockIso(0, 0),
    is_stale: false,
  }
}

export function mockCandles(symbol: string, timeframe: CandleTimeframe, count = 120): CandleSeries {
  const base = Number(mockQuote(symbol).price)
  const candles = []
  let close = base * 0.9
  for (let i = 0; i < count; i += 1) {
    const open = close
    const change = base * 0.006 * Math.sin(i / 5) + base * 0.0012
    close = open + change
    const high = Math.max(open, close) + base * 0.002
    const low = Math.min(open, close) - base * 0.002
    candles.push({
      time: mockIso(count - i, 0),
      open: open.toFixed(2),
      high: high.toFixed(2),
      low: low.toFixed(2),
      close: close.toFixed(2),
      volume: (20_000_000 + i * 120_000).toString(),
    })
  }
  return { symbol: symbol.toUpperCase(), timeframe, candles }
}

export function mockAsset(symbol: string): AssetDetail {
  const upper = symbol.toUpperCase()
  const item = WATCHLIST.find((entry) => entry.symbol === upper)
  return {
    asset: {
      symbol: upper,
      name: item?.name ?? upper,
      asset_class: 'EQUITY',
      exchange: 'NASDAQ',
      sector: 'Technology',
      currency: 'USD',
    },
    quote: mockQuote(upper),
    regime: item?.market_regime ?? 'SIDEWAYS',
    signals: mockSignals().filter((signal) => signal.symbol === upper),
    agent_summary:
      'Trend remains constructive while momentum improves; position sizing stays within portfolio limits.',
  }
}
