import type { PortfolioSnapshot, PortfolioSummary } from '~/types/portfolio'
import { MOCK_PORTFOLIO_ID, mockIso } from './helpers'

export function mockPortfolio(): PortfolioSummary {
  return {
    portfolio_id: MOCK_PORTFOLIO_ID,
    currency: 'USD',
    cash: '41250.75',
    equity: '127480.25',
    buying_power: '82501.50',
    invested: '86229.50',
    market_value: '86229.50',
    open_pnl: '1842.35',
    realized_pnl: '5320.10',
    unrealized_pnl: '1842.35',
    daily_pnl: '1842.35',
    total_pnl: '27480.25',
    total_return_pct: '27.48',
    daily_return_pct: '1.47',
    exposure_pct: '67.64',
    open_positions: 4,
    updated_at: mockIso(0, 0),
  }
}

export function mockPortfolioHistory(days = 90): PortfolioSnapshot[] {
  const points: PortfolioSnapshot[] = []
  let equity = 100000
  for (let i = days; i >= 0; i -= 1) {
    const drift = 0.0016 + Math.sin(i / 6) * 0.004
    equity *= 1 + drift
    const drawdown = i % 17 === 0 ? -0.01 : 0
    points.push({
      timestamp: mockIso(i),
      equity: equity.toFixed(2),
      cash: '41250.75',
      invested: (equity - 41250.75).toFixed(2),
      daily_pnl: (equity * drift).toFixed(2),
      total_return_pct: ((equity / 100000 - 1) * 100).toFixed(2),
      drawdown_pct: (drawdown * 100).toFixed(2),
      benchmark_equity: (100000 * (1 + (days - i) * 0.0009)).toFixed(2),
    })
  }
  return points
}
