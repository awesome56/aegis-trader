import type { Backtest, BacktestResult } from '~/types/backtest'
import { mockIso } from './helpers'

const BACKTESTS: Backtest[] = [
  {
    id: 'bt-1',
    name: 'Trend Following — AAPL',
    strategy_id: 'strat-trend',
    strategy_name: 'Trend Following',
    symbols: ['AAPL'],
    timeframe: '1d',
    start_date: '2025-01-01',
    end_date: '2025-06-01',
    initial_capital: '100000',
    benchmark_symbol: 'SPY',
    status: 'COMPLETED',
    created_at: mockIso(20),
    started_at: mockIso(20),
    completed_at: mockIso(20),
    error: null,
    final_capital: '112000',
    total_return_pct: '12.00',
    max_drawdown_pct: '6.20',
    num_trades: 8,
  },
  {
    id: 'bt-2',
    name: 'Momentum — MSFT',
    strategy_id: 'strat-momentum',
    strategy_name: 'Momentum',
    symbols: ['MSFT'],
    timeframe: '1d',
    start_date: '2025-01-01',
    end_date: '2025-06-01',
    initial_capital: '50000',
    benchmark_symbol: null,
    status: 'RUNNING',
    created_at: mockIso(0, 2),
    started_at: mockIso(0, 2),
    completed_at: null,
    error: null,
    final_capital: null,
    total_return_pct: null,
    max_drawdown_pct: null,
    num_trades: null,
  },
]

export function mockBacktests(): Backtest[] {
  return BACKTESTS.map((backtest) => ({ ...backtest }))
}

export function mockBacktestResult(id: string): BacktestResult | null {
  const found = BACKTESTS.find((backtest) => backtest.id === id)
  if (!found || found.status !== 'COMPLETED') return null
  const metrics = {
    initial_capital: found.initial_capital,
    final_capital: '112000',
    net_profit: '12000',
    total_return_pct: '12.00',
    benchmark_return_pct: '7.40',
    num_trades: 8,
    wins: 5,
    losses: 3,
    win_rate: '62.50',
    average_win: '3200',
    average_loss: '-1333.33',
    largest_win: '5200',
    largest_loss: '-2100',
    gross_profit: '16000',
    gross_loss: '-4000',
    profit_factor: '4.00',
    expectancy: '1500',
    max_drawdown: '6200',
    max_drawdown_pct: '6.20',
    sharpe_ratio: '1.42',
    sortino_ratio: '1.90',
    total_fees: '120',
    total_slippage: '80',
    average_holding_seconds: '86400',
    exposure_pct: '68.40',
  }
  return {
    backtest_id: found.id,
    engine_version: 'phase8-v1',
    strategy_config: { strategy: { key: 'trend_following' } },
    metrics,
    equity_curve: [
      { timestamp: mockIso(20), cash: '100000', positions_value: '0', equity: '100000', cumulative_return_pct: '0', drawdown_pct: '0' },
      { timestamp: mockIso(10), cash: '106000', positions_value: '0', equity: '106000', cumulative_return_pct: '6', drawdown_pct: '0' },
      { timestamp: mockIso(0, 0), cash: '112000', positions_value: '0', equity: '112000', cumulative_return_pct: '12', drawdown_pct: '0' },
    ],
    drawdown_curve: [
      { timestamp: mockIso(20), drawdown_pct: '0' },
      { timestamp: mockIso(10), drawdown_pct: '2.10' },
      { timestamp: mockIso(0, 0), drawdown_pct: '0' },
    ],
    monthly_returns: [
      { month: '2025-01', return_pct: '3.20' },
      { month: '2025-02', return_pct: '4.10' },
      { month: '2025-03', return_pct: '4.70' },
    ],
    trades: [
      {
        symbol: 'AAPL', side: 'LONG', quantity: '100',
        entry_time: mockIso(18), entry_price: '180.00',
        exit_time: mockIso(12), exit_price: '190.00',
        gross_pnl: '1000', fees: '15', slippage: '10', net_pnl: '975',
        return_pct: '5.42', holding_period_seconds: 518400, exit_reason: 'SIGNAL',
      },
    ],
  }
}
