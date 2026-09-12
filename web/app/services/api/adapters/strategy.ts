import type { MarketRegime, SignalDirection } from '~/types/market'
import type { StrategySignal } from '~/types/strategy'
import { iso, num } from './common'
import type { RawSignal } from './raw'

const DIRECTIONS: ReadonlySet<string> = new Set(['LONG', 'SHORT', 'NEUTRAL'])

function direction(value: string): SignalDirection {
  return (DIRECTIONS.has(value) ? value : 'NEUTRAL') as SignalDirection
}

export function toStrategySignal(raw: RawSignal): StrategySignal {
  return {
    id: raw.id,
    symbol: raw.symbol,
    strategy_id: raw.strategy_id,
    strategy_name: raw.strategy_name ?? raw.strategy_key ?? raw.strategy_id,
    direction: direction(raw.direction),
    strength: num(raw.strength),
    confidence: num(raw.confidence),
    timeframe: raw.timeframe,
    indicators: raw.indicators,
    market_regime: (raw.market_regime as MarketRegime | null) ?? null,
    signal_time: iso(raw.signal_time),
  }
}
