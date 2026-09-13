import type {
  AssetDetail,
  AssetSummary,
  Candle,
  CandleSeries,
  CandleTimeframe,
  MarketOverview,
  MarketRegime,
  Quote,
  SignalDirection,
  WatchlistItem,
} from '~/types/market'
import { iso, num } from './common'
import type {
  RawAssetSearch,
  RawCandle,
  RawCandleSeries,
  RawMarketOverview,
  RawMarketOverviewItem,
  RawQuote,
} from './raw'

const DIRECTION: ReadonlySet<string> = new Set(['LONG', 'SHORT', 'NEUTRAL'])

function direction(value: string | null): SignalDirection | null {
  if (!value || !DIRECTION.has(value)) {
    return value ? 'NEUTRAL' : null
  }
  return value as SignalDirection
}

function regime(value: string | null): MarketRegime | null {
  return value ? (value as MarketRegime) : null
}

const TIMEFRAMES: Record<string, CandleTimeframe> = {
  '1m': '1m',
  '5m': '5m',
  '15m': '15m',
  '30m': '1H',
  '1h': '1H',
  '4h': '4H',
  '1d': '1D',
  '1w': '1W',
}

function timeframe(value: string): CandleTimeframe {
  return TIMEFRAMES[value.toLowerCase()] ?? '1D'
}

export function toWatchlistItem(raw: RawMarketOverviewItem): WatchlistItem {
  return {
    symbol: raw.symbol,
    name: raw.name,
    price: raw.price ?? null,
    change_pct: raw.change_pct ?? null,
    volume: raw.volume,
    signal: direction(raw.signal_direction),
    market_regime: regime(raw.market_regime),
  }
}

export function toMarketOverview(raw: RawMarketOverview): MarketOverview {
  const regimes = raw.items.map((item) => item.market_regime).filter(Boolean)
  return {
    regime: (regimes[0] as MarketRegime | undefined) ?? 'UNKNOWN',
    as_of: iso(raw.status.timestamp),
    items: raw.items.map(toWatchlistItem),
  }
}

export function toQuote(raw: RawQuote): Quote {
  const last = Number(num(raw.last))
  const previousClose = raw.previous_close === null ? null : Number(raw.previous_close)
  const change = previousClose === null ? 0 : last - previousClose
  const changePct = previousClose ? (change / previousClose) * 100 : 0
  return {
    symbol: raw.symbol,
    price: raw.last,
    bid: raw.bid,
    ask: raw.ask,
    change: change.toFixed(2),
    change_pct: changePct.toFixed(2),
    volume: raw.volume,
    day_high: raw.high,
    day_low: raw.low,
    market_regime: null,
    quote_time: iso(raw.market_timestamp),
    is_stale: raw.is_stale,
  }
}

function toCandle(raw: RawCandle): Candle {
  return {
    time: iso(raw.close_time ?? raw.open_time),
    open: raw.open,
    high: raw.high,
    low: raw.low,
    close: raw.close,
    volume: raw.volume,
  }
}

export function toCandleSeries(raw: RawCandleSeries): CandleSeries {
  return {
    symbol: raw.symbol,
    timeframe: timeframe(raw.timeframe),
    candles: raw.candles.map(toCandle),
  }
}

export function toWatchlistSearch(results: RawAssetSearch[]): WatchlistItem[] {
  return results.map((result) => ({
    symbol: result.symbol,
    name: result.name,
    price: null,
    change_pct: null,
    volume: null,
    signal: null,
    market_regime: null,
  }))
}

export function toAssetSummary(raw: RawAssetSearch): AssetSummary {
  return {
    symbol: raw.symbol,
    name: raw.name,
    asset_class: raw.asset_class,
    exchange: raw.exchange,
    sector: null,
    currency: raw.currency,
  }
}

export function toAssetDetail(asset: AssetSummary, quote: Quote | null): AssetDetail {
  return {
    asset,
    quote,
    regime: quote?.market_regime ?? null,
    signals: [],
    agent_summary: null,
  }
}
