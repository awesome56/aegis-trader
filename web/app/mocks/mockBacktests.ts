import type { Backtest, BacktestResult } from '~/types/backtest'
import { mockIso } from './helpers'

const BACKTESTS: Backtest[] = [
  {
    id: 'bt-1',
    name: 'Trend Following — Large Cap',
    strategy_id: 'strat-trend',
    strategy_name: 'Trend Following',
    symbols: ['AAPL', 'MSFT', 'NVDA'],
    timeframe: '1d',
    start_date: '2023-01-01T00:00:00.000Z',
    end_date: '2025-01-01T00:00:00.000Z',
    initial_capital: '100000.00',
    status: 'COMPLETED',
    created_at: mockIso(20),
    completed_at: mockIso(20),
    error: null,
  },
  {
    id: 'bt-2',
    name: 'Momentum — Tech',
    strategy_id: 'strat-momentum',
    strategy_name: 'Momentum',
    symbols: ['NVDA', 'AMD', 'AVGO'],
    timeframe: '1d',
    start_date: '2024-01-01T00:00:00.000Z',
    end_date: '2025-06-01T00:00:00.000Z',
    initial_capital: '50000.00',
    status: 'RUNNING',
    created_at: mockIso(0, 2),
    completed_at: null,
    error: null,
  },
]

export function mockBacktests(): Backtest[] {
  return BACKTESTS.map((backtest) => ({ ...backtest }))
}

export function mockBacktestResult(id: string): BacktestResult | null {
  const backtest = BACKTESTS.find((entry) => entry.id === id)
  if (!backtest || backtest.status !== 'COMPLETED') return null
  const points = []
  let equity = 100000
  for (let i = 0; i < 240; i += 1) {
    equity *= 1 + 0.0009 + Math.sin(i / 8) * 0.003
    points.push({
      time: mockIso(240 - i),
      equity: equity.toFixed(2),
      benchmark: (100000 * (1 + i * 0.0006)).toFixed(2),
      drawdown_pct: (i % 23 === 0 ? -2.1 : -0.4).toFixed(2),
    })
  }
  return {
    backtest,
    metrics: {
      initial_capital: '100000.00',
      final_capital: '138420.00',
      total_return_pct: '38.42',
      benchmark_return_pct: '14.20',
      max_drawdown_pct: '9.80',
      sharpe_ratio: '1.51',
      sortino_ratio: '2.04',
      num_trades: 68,
      wins: 41,
      losses: 27,
      win_rate: '60.29',
      average_win: '642.10',
      average_loss: '-318.40',
      profit_factor: '2.16',
      expectancy: '261.75',
      exposure_pct: '64.30',
      fees: '412.00',
      slippage: '286.50',
    },
    equity_curve: points,
    monthly_returns: [
      { month: '2024-01', return_pct: '2.10' },
      { month: '2024-02', return_pct: '-1.40' },
      { month: '2024-03', return_pct: '3.80' },
      { month: '2024-04', return_pct: '1.20' },
      { month: '2024-05', return_pct: '-0.60' },
      { month: '2024-06', return_pct: '4.10' },
    ],
    trades: [
      {
        symbol: 'NVDA',
        side: 'BUY',
        quantity: '40',
        entry_price: '118.42',
        exit_price: '126.85',
        pnl: '337.20',
        return_pct: '7.12',
        opened_at: mockIso(60),
        closed_at: mockIso(30),
      },
    ],
  }
}
