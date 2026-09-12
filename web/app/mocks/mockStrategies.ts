import type { Strategy, StrategyDetail, StrategySignal } from '~/types/strategy'
import { mockIso } from './helpers'

const STRATEGIES: Strategy[] = [
  {
    id: 'strat-trend',
    name: 'Trend Following',
    slug: 'trend-following',
    description: 'Rides sustained directional moves using moving-average structure.',
    type: 'TREND_FOLLOWING',
    is_enabled: true,
    health: 'HEALTHY',
    timeframe: '1d',
    asset_classes: ['EQUITY', 'ETF'],
    performance: {
      trade_count: 42,
      win_rate: '57.1',
      return_pct: '12.40',
      profit_factor: '1.85',
      max_drawdown_pct: '6.20',
      sharpe_ratio: '1.42',
    },
    updated_at: mockIso(0, 0),
  },
  {
    id: 'strat-momentum',
    name: 'Momentum',
    slug: 'momentum',
    description: 'Buys strength confirmed by price and volume expansion.',
    type: 'MOMENTUM',
    is_enabled: true,
    health: 'HEALTHY',
    timeframe: '1d',
    asset_classes: ['EQUITY'],
    performance: {
      trade_count: 31,
      win_rate: '51.6',
      return_pct: '9.10',
      profit_factor: '1.62',
      max_drawdown_pct: '8.10',
      sharpe_ratio: '1.18',
    },
    updated_at: mockIso(0, 0),
  },
  {
    id: 'strat-meanrev',
    name: 'Mean Reversion',
    slug: 'mean-reversion',
    description: 'Fades statistically stretched moves back toward the mean.',
    type: 'MEAN_REVERSION',
    is_enabled: false,
    health: 'DISABLED',
    timeframe: '1d',
    asset_classes: ['EQUITY'],
    performance: {
      trade_count: 18,
      win_rate: '61.1',
      return_pct: '4.30',
      profit_factor: '1.30',
      max_drawdown_pct: '5.40',
      sharpe_ratio: '0.94',
    },
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
    parameters: { fast_period: 20, slow_period: 50, atr_multiple: 2 },
    recent_signals: mockSignals().filter((signal) => signal.strategy_id === id),
  }
}

export function mockSignals(): StrategySignal[] {
  return [
    {
      id: 'sig-1',
      symbol: 'NVDA',
      strategy_id: 'strat-momentum',
      strategy_name: 'Momentum',
      direction: 'LONG',
      strength: '0.82',
      confidence: '0.78',
      timeframe: '1d',
      indicators: { rsi: 63.4, macd: 1.84 },
      market_regime: 'BULLISH',
      signal_time: mockIso(0, 1),
    },
    {
      id: 'sig-2',
      symbol: 'AAPL',
      strategy_id: 'strat-trend',
      strategy_name: 'Trend Following',
      direction: 'LONG',
      strength: '0.64',
      confidence: '0.71',
      timeframe: '1d',
      indicators: { sma_fast: 218.2, sma_slow: 211.7 },
      market_regime: 'BULLISH',
      signal_time: mockIso(0, 2),
    },
    {
      id: 'sig-3',
      symbol: 'TSLA',
      strategy_id: 'strat-meanrev',
      strategy_name: 'Mean Reversion',
      direction: 'SHORT',
      strength: '0.55',
      confidence: '0.62',
      timeframe: '1d',
      indicators: { bollinger_z: 2.1 },
      market_regime: 'HIGH_VOLATILITY',
      signal_time: mockIso(0, 3),
    },
  ]
}
