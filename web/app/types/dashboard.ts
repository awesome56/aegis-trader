import type { AgentDecision, AgentStatus, TradeProposal } from './agent'
import type { StrategySignal } from './strategy'
import type { PortfolioSnapshot, PortfolioSummary } from './portfolio'
import type { Position } from './position'
import type { RiskStatus } from './risk'
import type { Trade } from './trade'

export interface DashboardData {
  summary: {
    portfolio: PortfolioSummary
    risk: RiskStatus
    agent: AgentStatus
    trades_today: number
    proposals_today: number
  }
  top_positions: Position[]
  recent_trades: Trade[]
  recent_decisions: AgentDecision[]
  recent_proposals: TradeProposal[]
  strategy_signals: StrategySignal[]
  equity_history: PortfolioSnapshot[]
}
