import type { Strategy, StrategyDetail, StrategySignal } from '~/types/strategy'
import { mockIso } from './helpers'

const STRATEGIES: Strategy[] = [
  {
    id: 'strat-trend',
    key: 'trend-following',
    name: 'Trend Following',
    description: 'Rides sustained directional moves using moving-average structure.',
    strategy_type: 'TREND_FOLLOWING',
    is_enabled: true,
    timeframe: '1d',
    priority: 10,
    parameters: { fast_period: 20, slow_period: 50, atr_multiple: 2 },
    asset_classes: ['EQUITY', 'ETF'],
    signal_count: 42,
    last_signal_at: mockIso(0, 2),
    created_at: mockIso(40),
    updated_at: mockIso(0, 0),
  },
  {
    id: 'strat-momentum',
    key: 'momentum',
    name: 'Momentum',
    description: 'Buys strength confirmed by price and volume expansion.',
    strategy_type: 'MOMENTUM',
    is_enabled: true,
    timeframe: '1d',
    priority: 20,
    parameters: { rsi_period: 14, macd_fast: 12, macd_slow: 26 },
    asset_classes: ['EQUITY'],
    signal_count: 31,
    last_signal_at: mockIso(0, 1),
    created_at: mockIso(40),
    updated_at: mockIso(0, 0),
  },
  {
    id: 'strat-meanrev',
    key: 'mean-reversion',
    name: 'Mean Reversion',
    description: 'Fades statistically stretched moves back toward the mean.',
    strategy_type: 'MEAN_REVERSION',
    is_enabled: false,
    timeframe: '1d',
    priority: 30,
    parameters: { bollinger_period: 20, bollinger_std: 2 },
    asset_classes: ['EQUITY'],
    signal_count: 18,
    last_signal_at: mockIso(0, 3),
    created_at: mockIso(40),
    updated_at: mockIso(1),
  },
]

export function mockStrategies(): Strategy[] {
  return STRATEGIES.map((strategy) => ({ ...strategy }))
}

export function mockStrategy(id: string): StrategyDetail | null {
  const found = STRATEGIES.find((strategy) => strategy.id === id)
  if (!found) return null
  return {
    ...found,
    recent_signals: mockSignals().filter((signal) => signal.strategy_id === id),
  }
}

export function mockSignals(): StrategySignal[] {
  return [
    {
      id: 'sig-1',
      strategy_id: 'strat-momentum',
      strategy_key: 'momentum',
      strategy_name: 'Momentum',
      symbol: 'NVDA',
      direction: 'LONG',
      strength: '0.82',
      confidence: '0.78',
      price: '126.50',
      timeframe: '1d',
      time_horizon: 'SWING',
      indicators: { rsi: 63.4, macd: 1.84, signal: 0.93, histogram: 0.25, relative_volume: 1.42 },
      market_regime: 'BULLISH',
      signal_time: mockIso(0, 1),
      data_timestamp: mockIso(0, 1),
      expires_at: mockIso(-1, -1),
    },
    {
      id: 'sig-2',
      strategy_id: 'strat-trend',
      strategy_key: 'trend-following',
      strategy_name: 'Trend Following',
      symbol: 'AAPL',
      direction: 'LONG',
      strength: '0.64',
      confidence: '0.71',
      price: '221.05',
      timeframe: '1d',
      time_horizon: 'SWING',
      indicators: { sma_fast: 218.2, sma_slow: 211.7, atr: 4.1, trend_strength: 0.55 },
      market_regime: 'BULLISH',
      signal_time: mockIso(0, 2),
      data_timestamp: mockIso(0, 2),
      expires_at: mockIso(-1, -2),
    },
    {
      id: 'sig-3',
      strategy_id: 'strat-meanrev',
      strategy_key: 'mean-reversion',
      strategy_name: 'Mean Reversion',
      symbol: 'TSLA',
      direction: 'SHORT',
      strength: '0.55',
      confidence: '0.62',
      price: '236.40',
      timeframe: '1d',
      time_horizon: 'SWING',
      indicators: { bollinger_upper: 250.1, bollinger_middle: 240.0, bollinger_lower: 229.9, percent_b: 0.95, rsi: 71.2 },
      market_regime: 'HIGH_VOLATILITY',
      signal_time: mockIso(0, 3),
      data_timestamp: mockIso(0, 3),
      expires_at: mockIso(-1, -3),
    },
  ]
}
