import type { ISODateString, Numeric } from './api'

export type MarketRegime =
  | 'BULLISH'
  | 'BEARISH'
  | 'SIDEWAYS'
  | 'HIGH_VOLATILITY'
  | 'LOW_VOLATILITY'
  | 'UNKNOWN'

export type SignalDirection = 'LONG' | 'SHORT' | 'NEUTRAL'

export type CandleTimeframe = '1m' | '5m' | '15m' | '1H' | '4H' | '1D' | '1W'

export interface Quote {
  symbol: string
  price: Numeric
  bid: Numeric | null
  ask: Numeric | null
  change: Numeric
  change_pct: Numeric
  volume: Numeric | null
  day_high: Numeric | null
  day_low: Numeric | null
  market_regime: MarketRegime | null
  quote_time: ISODateString
  is_stale: boolean
}

export interface Candle {
  time: ISODateString
  open: Numeric
  high: Numeric
  low: Numeric
  close: Numeric
  volume: Numeric | null
}

export interface CandleSeries {
  symbol: string
  timeframe: CandleTimeframe
  candles: Candle[]
}

export interface IndicatorPoint {
  time: ISODateString
  value: Numeric
}

export interface IndicatorSet {
  symbol: string
  timeframe: CandleTimeframe
  sma?: Record<string, IndicatorPoint[]>
  ema?: Record<string, IndicatorPoint[]>
  rsi?: IndicatorPoint[]
  macd?: { macd: IndicatorPoint[]; signal: IndicatorPoint[]; histogram: IndicatorPoint[] }
  atr?: IndicatorPoint[]
  bollinger?: { upper: IndicatorPoint[]; middle: IndicatorPoint[]; lower: IndicatorPoint[] }
}

export interface WatchlistItem {
  symbol: string
  name: string | null
  price: Numeric | null
  bid: Numeric | null
  ask: Numeric | null
  previous_close: Numeric | null
  change: Numeric | null
  change_pct: Numeric | null
  day_high: Numeric | null
  day_low: Numeric | null
  volume: Numeric | null
  signal: SignalDirection | null
  market_regime: MarketRegime | null
  confidence: Numeric | null
  strategy: string | null
  quote_time: ISODateString | null
  age_seconds: number | null
  is_stale: boolean
}

export interface MarketOverview {
  regime: MarketRegime
  provider: string
  is_open: boolean
  session: string
  as_of: ISODateString
  items: WatchlistItem[]
}

export interface AssetSummary {
  symbol: string
  name: string | null
  asset_class: string
  exchange: string | null
  sector: string | null
  currency: string
}

export interface AssetDetail {
  asset: AssetSummary
  quote: Quote | null
  regime: MarketRegime | null
  signals: import('./strategy').StrategySignal[]
  agent_summary: string | null
}
