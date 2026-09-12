import type { ISODateString, Numeric } from './api'
import type { MarketRegime, SignalDirection } from './market'

export type StrategyType = 'TREND_FOLLOWING' | 'MOMENTUM' | 'MEAN_REVERSION' | 'CUSTOM'
export type StrategyHealth = 'HEALTHY' | 'DEGRADED' | 'DISABLED'

export interface StrategySignal {
  id: string
  symbol: string
  strategy_id: string
  strategy_name: string
  direction: SignalDirection
  strength: Numeric
  confidence: Numeric
  timeframe: string
  indicators: Record<string, Numeric> | null
  market_regime: MarketRegime | null
  signal_time: ISODateString
}

export interface StrategyPerformance {
  trade_count: number
  win_rate: Numeric
  return_pct: Numeric
  profit_factor: Numeric | null
  max_drawdown_pct: Numeric
  sharpe_ratio: Numeric | null
}

export interface Strategy {
  id: string
  name: string
  slug: string
  description: string | null
  type: StrategyType
  is_enabled: boolean
  health: StrategyHealth
  timeframe: string
  asset_classes: string[]
  performance: StrategyPerformance | null
  updated_at: ISODateString
}

export interface StrategyDetail extends Strategy {
  parameters: Record<string, unknown>
  recent_signals: StrategySignal[]
}
