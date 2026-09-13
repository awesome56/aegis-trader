import type { TimeHorizon } from './agent'
import type { ISODateString, Numeric } from './api'
import type { MarketRegime, SignalDirection } from './market'

export type StrategyType = 'TREND_FOLLOWING' | 'MOMENTUM' | 'MEAN_REVERSION' | 'CUSTOM'

export type EvaluationStatus = 'SIGNAL' | 'NO_SIGNAL' | 'INSUFFICIENT_DATA' | 'STALE_DATA'

export interface StrategySignal {
  id: string
  strategy_id: string
  strategy_key: string | null
  strategy_name: string | null
  symbol: string
  direction: SignalDirection
  strength: Numeric
  confidence: Numeric
  price: Numeric | null
  timeframe: string
  time_horizon: TimeHorizon | null
  market_regime: MarketRegime | null
  indicators: Record<string, Numeric> | null
  signal_time: ISODateString
  data_timestamp: ISODateString | null
  expires_at: ISODateString | null
}

export interface Strategy {
  id: string
  key: string
  name: string
  description: string | null
  strategy_type: StrategyType
  is_enabled: boolean
  timeframe: string
  priority: number
  parameters: Record<string, unknown> | null
  asset_classes: string[] | null
  signal_count: number
  last_signal_at: ISODateString | null
  created_at: ISODateString
  updated_at: ISODateString
}

export interface StrategyDetail extends Strategy {
  recent_signals: StrategySignal[]
}

export interface StrategySignalPage {
  items: StrategySignal[]
  total: number
  page: number
  pageSize: number
}

export interface SignalEvidence {
  strategy_key: string
  strategy_name: string
  symbol: string
  direction: SignalDirection
  strength: Numeric
  confidence: Numeric
  price: Numeric | null
  timeframe: string
  time_horizon: TimeHorizon
  market_regime: MarketRegime
  indicators: Record<string, Numeric>
  generated_at: ISODateString
  data_timestamp: ISODateString
  expires_at: ISODateString
}

export interface StrategyEvaluation {
  strategy_key: string
  strategy_name: string
  symbol: string
  timeframe: string
  status: EvaluationStatus
  reason: string
  signal: SignalEvidence | null
}
