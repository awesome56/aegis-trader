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

function wl(
  symbol: string,
  name: string,
  price: number,
  changePct: number,
  volume: number,
  signal: WatchlistItem['signal'],
  regime: WatchlistItem['market_regime'],
  strategy: string | null = null,
): WatchlistItem {
  const previous = price / (1 + changePct / 100)
  return {
    symbol,
    name,
    provider: 'mock',
    price: price.toFixed(2),
    bid: (price - 0.02).toFixed(2),
    ask: (price + 0.02).toFixed(2),
    previous_close: previous.toFixed(2),
    change: (price - previous).toFixed(2),
    change_pct: changePct.toFixed(2),
    change_window: 'prev_close',
    day_high: (price * 1.015).toFixed(2),
    day_low: (price * 0.985).toFixed(2),
    volume: volume.toString(),
    signal,
    market_regime: regime,
    confidence: signal ? '0.72' : null,
    strategy,
    quote_time: mockIso(0, 0),
    last_candle_time: mockIso(0, 0),
    signal_time: signal ? mockIso(0, 0) : null,
    signal_expires_at: null,
    age_seconds: 12,
    is_stale: false,
    market_closed: false,
    session: 'OPEN',
  }
}

const WATCHLIST: WatchlistItem[] = [
  wl('NVDA', 'NVIDIA Corporation', 126.85, 2.14, 41_200_000, 'LONG', 'BULLISH', 'momentum'),
  wl('AAPL', 'Apple Inc.', 221.05, 0.42, 28_100_000, 'LONG', 'BULLISH', 'trend-following'),
  wl('MSFT', 'Microsoft Corporation', 410.55, -0.31, 19_900_000, 'NEUTRAL', 'SIDEWAYS'),
  wl('TSLA', 'Tesla, Inc.', 236.4, -1.82, 35_600_000, 'SHORT', 'HIGH_VOLATILITY', 'mean-reversion'),
  wl('AMZN', 'Amazon.com, Inc.', 188.4, 1.05, 22_700_000, 'NEUTRAL', 'SIDEWAYS'),
]

export function mockMarkets(): MarketOverview {
  return {
    regime: 'BULLISH',
    provider: 'mock',
    is_open: true,
    session: 'REGULAR',
    as_of: mockIso(0, 0),
    items: WATCHLIST.map((item) => ({ ...item })),
  }
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
