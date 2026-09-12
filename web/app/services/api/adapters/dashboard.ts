import type { DashboardData } from '~/types/dashboard'
import { toAgentStatusDisabled } from './agent'
import { int } from './common'
import { toPortfolioHistory, toPortfolioSummary } from './portfolio'
import { toPosition } from './positions'
import { toProposalPage } from './proposals'
import type {
  RawDashboard,
  RawPortfolioHistory,
  RawPositionValuation,
  RawProposalPage,
  RawTradePage,
} from './raw'
import { toRiskStatus } from './risk'
import { toStrategySignal } from './strategy'
import { toTradePage } from './trades'

export interface DashboardSource {
  dashboard: RawDashboard
  positions: RawPositionValuation[]
  history: RawPortfolioHistory
  trades: RawTradePage
  proposals: RawProposalPage
}

export function toDashboardData(source: DashboardSource): DashboardData {
  const { dashboard } = source
  const portfolio = toPortfolioSummary(dashboard.portfolio)
  const risk = toRiskStatus({
    portfolio: dashboard.portfolio,
    riskStatus: dashboard.risk_status,
    utilizations: dashboard.risk_utilizations,
  })

  const tradesToday = dashboard.risk_utilizations.find((row) => row.key === 'trades_today')
  const recentProposals = toProposalPage(source.proposals).items
  const topPositions = source.positions
    .map(toPosition)
    .sort((a, b) => Number(b.market_value) - Number(a.market_value))
    .slice(0, 5)

  return {
    summary: {
      portfolio,
      risk,
      agent: toAgentStatusDisabled(),
      trades_today: tradesToday ? int(tradesToday.current) : 0,
      proposals_today: recentProposals.length,
    },
    top_positions: topPositions,
    recent_trades: toTradePage(source.trades).items,
    recent_decisions: [],
    recent_proposals: recentProposals,
    strategy_signals: dashboard.recent_signals.map(toStrategySignal),
    equity_history: toPortfolioHistory(source.history).points,
  }
}
