import type { DashboardData } from '~/types/dashboard'
import { mockAgentStatus, mockDecisions, mockProposals } from './mockAgent'
import { mockPortfolio, mockPortfolioHistory } from './mockPortfolio'
import { mockPositions } from './mockPositions'
import { mockRiskStatus } from './mockRisk'
import { mockSignals } from './mockStrategies'
import { mockTrades } from './mockTrades'

export function mockDashboard(): DashboardData {
  return {
    summary: {
      portfolio: mockPortfolio(),
      risk: mockRiskStatus(),
      agent: mockAgentStatus(),
      trades_today: 3,
      proposals_today: 3,
    },
    top_positions: mockPositions(),
    recent_trades: mockTrades(),
    recent_decisions: mockDecisions(),
    recent_proposals: mockProposals(),
    strategy_signals: mockSignals(),
    equity_history: mockPortfolioHistory(30),
  }
}
