import type { TimeHorizon } from '~/types/agent'
import type { MarketRegime, SignalDirection } from '~/types/market'
import type {
  EvaluationStatus,
  SignalEvidence,
  Strategy,
  StrategyDetail,
  StrategyEvaluation,
  StrategySignal,
  StrategySignalPage,
  StrategyType,
} from '~/types/strategy'
import { iso, isoOrNull, num } from './common'
import type {
  RawSignal,
  RawSignalEvidence,
  RawSignalPage,
  RawStrategy,
  RawStrategyDetail,
  RawStrategyEvaluation,
} from './raw'

const DIRECTIONS: ReadonlySet<string> = new Set(['LONG', 'SHORT', 'NEUTRAL'])

function direction(value: string): SignalDirection {
  return (DIRECTIONS.has(value) ? value : 'NEUTRAL') as SignalDirection
}

export function toStrategySignal(raw: RawSignal): StrategySignal {
  return {
    id: raw.id,
    strategy_id: raw.strategy_id,
    strategy_key: raw.strategy_key,
    strategy_name: raw.strategy_name ?? raw.strategy_key,
    symbol: raw.symbol,
    direction: direction(raw.direction),
    strength: num(raw.strength),
    confidence: num(raw.confidence),
    price: raw.price,
    timeframe: raw.timeframe,
    time_horizon: (raw.time_horizon as TimeHorizon | null) ?? null,
    market_regime: (raw.market_regime as MarketRegime | null) ?? null,
    indicators: raw.indicators,
    signal_time: iso(raw.signal_time),
    data_timestamp: isoOrNull(raw.data_timestamp),
    expires_at: isoOrNull(raw.expires_at),
  }
}

export function toStrategySignalPage(raw: RawSignalPage): StrategySignalPage {
  return {
    items: raw.items.map(toStrategySignal),
    total: raw.total,
    page: raw.page,
    pageSize: raw.page_size,
  }
}

export function toStrategy(raw: RawStrategy): Strategy {
  return {
    id: raw.id,
    key: raw.key,
    name: raw.name,
    description: raw.description,
    strategy_type: raw.strategy_type as StrategyType,
    is_enabled: raw.is_enabled,
    timeframe: raw.timeframe,
    priority: raw.priority,
    parameters: raw.parameters,
    asset_classes: raw.asset_classes,
    signal_count: raw.signal_count,
    last_signal_at: isoOrNull(raw.last_signal_at),
    created_at: iso(raw.created_at),
    updated_at: iso(raw.updated_at),
  }
}

export function toStrategyDetail(raw: RawStrategyDetail): StrategyDetail {
  return {
    ...toStrategy(raw),
    recent_signals: (raw.recent_signals ?? []).map(toStrategySignal),
  }
}

function toSignalEvidence(raw: RawSignalEvidence): SignalEvidence {
  return {
    strategy_key: raw.strategy_key,
    strategy_name: raw.strategy_name,
    symbol: raw.symbol,
    direction: direction(raw.direction),
    strength: num(raw.strength),
    confidence: num(raw.confidence),
    price: raw.price,
    timeframe: raw.timeframe,
    time_horizon: raw.time_horizon as TimeHorizon,
    market_regime: raw.market_regime as MarketRegime,
    indicators: raw.indicators ?? {},
    generated_at: iso(raw.generated_at),
    data_timestamp: iso(raw.data_timestamp),
    expires_at: iso(raw.expires_at),
  }
}

export function toStrategyEvaluation(raw: RawStrategyEvaluation): StrategyEvaluation {
  return {
    strategy_key: raw.strategy_key,
    strategy_name: raw.strategy_name,
    symbol: raw.symbol,
    timeframe: raw.timeframe,
    status: raw.status as EvaluationStatus,
    reason: raw.reason,
    signal: raw.signal ? toSignalEvidence(raw.signal) : null,
  }
}
