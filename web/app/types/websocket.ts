import type { ISODateString, Numeric } from './api'
import type { MarketRegime } from './market'
import type { KillSwitchState } from './system'

/**
 * WebSocket event wire format.
 *
 * Envelope: { "event": "order.filled", "timestamp": "...", "data": { ... } }
 * Event names are a discriminated union so handlers are exhaustive and no
 * `any` is required.
 */

export const WS_EVENTS = {
  portfolioUpdated: 'portfolio.updated',
  positionUpdated: 'position.updated',
  positionCreated: 'position.created',
  positionClosed: 'position.closed',
  quoteUpdated: 'quote.updated',
  proposalCreated: 'proposal.created',
  proposalRiskApproved: 'proposal.risk_approved',
  proposalRiskRejected: 'proposal.risk_rejected',
  proposalExecutionStarted: 'proposal.execution_started',
  proposalExecuted: 'proposal.executed',
  proposalFailed: 'proposal.failed',
  proposalCancelled: 'proposal.cancelled',
  orderCreated: 'order.created',
  orderSubmitted: 'order.submitted',
  orderPartiallyFilled: 'order.partially_filled',
  orderFilled: 'order.filled',
  orderCancelled: 'order.cancelled',
  orderRejected: 'order.rejected',
  executionCreated: 'execution.created',
  tradeCompleted: 'trade.completed',
  riskWarning: 'risk.warning',
  riskCritical: 'risk.critical',
  riskEvaluationCreated: 'risk.evaluation_created',
  riskTradingStateChanged: 'risk.trading_state_changed',
  strategySignal: 'strategy.signal',
  strategyEnabled: 'strategy.enabled',
  strategyDisabled: 'strategy.disabled',
  notificationCreated: 'notification.created',
  backtestCreated: 'backtest.created',
  backtestStarted: 'backtest.started',
  backtestCompleted: 'backtest.completed',
  backtestFailed: 'backtest.failed',
  backtestCancelled: 'backtest.cancelled',
  agentStarted: 'agent.started',
  agentAssetAnalysis: 'agent.asset_analysis',
  agentCompleted: 'agent.completed',
  systemStatusChanged: 'system.status_changed',
  brokerConnected: 'broker.connected',
  brokerDisconnected: 'broker.disconnected',
} as const

export type WebSocketEventName = (typeof WS_EVENTS)[keyof typeof WS_EVENTS]

export interface WebSocketEnvelope<T = unknown> {
  event: WebSocketEventName | string
  timestamp: ISODateString
  data: T
}

export const WS_STATUS_EVENTS = ['system.status_changed'] as const

// --- Event payloads ---------------------------------------------------------

export interface PortfolioUpdatedEvent {
  event: 'portfolio.updated'
  timestamp: ISODateString
  data: {
    portfolio_id: string
    equity: Numeric
    cash: Numeric
    buying_power: Numeric
    daily_pnl: Numeric
    total_return_pct: Numeric
    exposure_pct: Numeric
    open_positions: number
  }
}

export interface PositionUpdatedEvent {
  event: 'position.updated'
  timestamp: ISODateString
  data: { position_id: string; symbol: string; current_price: Numeric; unrealized_pnl: Numeric }
}

export interface QuoteUpdatedEvent {
  event: 'quote.updated'
  timestamp: ISODateString
  data: { symbol: string; price: Numeric; change_pct: Numeric; quote_time: ISODateString }
}

export interface ProposalCreatedEvent {
  event: 'proposal.created'
  timestamp: ISODateString
  data: { proposal_id: string; symbol: string; action: string; confidence: Numeric }
}

export interface ProposalResolvedEvent {
  event: 'proposal.approved' | 'proposal.rejected'
  timestamp: ISODateString
  data: { proposal_id: string; symbol: string; reason?: string }
}

export interface OrderLifecycleEvent {
  event:
    | 'order.created'
    | 'order.submitted'
    | 'order.partially_filled'
    | 'order.filled'
    | 'order.cancelled'
    | 'order.failed'
  timestamp: ISODateString
  data: {
    order_id: string
    symbol: string
    side: string
    status: string
    filled_quantity?: Numeric
    average_fill_price?: Numeric
    error?: string
  }
}

export interface TradeCompletedEvent {
  event: 'trade.completed'
  timestamp: ISODateString
  data: { trade_id: string; symbol: string; pnl: Numeric; return_pct: Numeric }
}

export interface RiskAlertEvent {
  event: 'risk.warning' | 'risk.critical'
  timestamp: ISODateString
  data: { level: 'WARNING' | 'CRITICAL'; message: string; symbol?: string }
}

export interface AgentLifecycleEvent {
  event: 'agent.started' | 'agent.asset_analysis' | 'agent.completed'
  timestamp: ISODateString
  data: { run_id?: string; symbol?: string; message?: string; decisions?: number }
}

export interface StrategySignalEvent {
  event: 'strategy.signal'
  timestamp: ISODateString
  data: {
    signal_id: string
    symbol: string
    strategy_id: string
    direction: string
    confidence: Numeric
  }
}

export interface SystemStatusEvent {
  event: 'system.status_changed'
  timestamp: ISODateString
  data: { kill_switch_state: KillSwitchState; trading_mode: 'paper' | 'live' }
}

export interface BrokerStatusEvent {
  event: 'broker.connected' | 'broker.disconnected'
  timestamp: ISODateString
  data: { broker: string; detail?: string }
}

/** Discriminated union of all known events. */
export type TradingEvent =
  | PortfolioUpdatedEvent
  | PositionUpdatedEvent
  | QuoteUpdatedEvent
  | ProposalCreatedEvent
  | ProposalResolvedEvent
  | OrderLifecycleEvent
  | TradeCompletedEvent
  | RiskAlertEvent
  | AgentLifecycleEvent
  | StrategySignalEvent
  | SystemStatusEvent
  | BrokerStatusEvent

/** An event we do not yet model — surfaced but never silently dropped. */
export interface UnknownTradingEvent {
  event: string
  timestamp: ISODateString
  data: Record<string, unknown>
}

export type AnyTradingEvent = TradingEvent | UnknownTradingEvent

export interface MarketRegimePayload {
  regime: MarketRegime
}
