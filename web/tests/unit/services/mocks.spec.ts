import { describe, expect, it } from 'vitest'
import {
  mockDashboard,
  mockPortfolio,
  mockPositions,
  mockProposals,
  mockRiskLimits,
  mockStrategies,
} from '~/mocks'

describe('mock fixtures', () => {
  it('exposes a complete dashboard composition', () => {
    const dashboard = mockDashboard()
    expect(dashboard.summary.portfolio.equity).toBeTruthy()
    expect(dashboard.top_positions.length).toBeGreaterThan(0)
    expect(dashboard.equity_history.length).toBeGreaterThan(0)
  })

  it('uses backend-shaped decimal strings for money', () => {
    const portfolio = mockPortfolio()
    expect(typeof portfolio.equity).toBe('string')
    expect(typeof portfolio.daily_pnl).toBe('string')
  })

  it('returns positions and proposals with required identifiers', () => {
    for (const position of mockPositions()) {
      expect(position.id).toBeTruthy()
      expect(position.symbol).toBeTruthy()
    }
    for (const proposal of mockProposals()) {
      expect(['PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'EXECUTED', 'CANCELLED']).toContain(
        proposal.status,
      )
    }
  })

  it('returns strategies and risk limits', () => {
    expect(mockStrategies().map((s) => s.slug)).toContain('trend-following')
    expect(mockRiskLimits().length).toBeGreaterThan(0)
  })
})
