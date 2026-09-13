import type { QueryClient } from '@tanstack/vue-query'
import type { AnyTradingEvent } from '~/types/websocket'
import { WS_EVENTS } from '~/types/websocket'
import { queryKeys } from '../api/keys'

/**
 * Route incoming WebSocket events to targeted TanStack Query cache updates.
 *
 * We invalidate only the queries each event can affect (never the whole app).
 * When an event carries a resource id we also invalidate that detail query.
 */
export function applyEventToCache(queryClient: QueryClient, event: AnyTradingEvent): void {
  const invalidate = (queryKey: readonly unknown[]) =>
    void queryClient.invalidateQueries({ queryKey })
  const data = (event.data ?? {}) as Record<string, unknown>
  const proposalId = typeof data.proposal_id === 'string' ? data.proposal_id : null

  const invalidateProposal = () => {
    invalidate(queryKeys.proposalsRoot)
    if (proposalId) invalidate(queryKeys.proposal(proposalId))
  }

  switch (event.event) {
    case WS_EVENTS.proposalCreated:
      invalidateProposal()
      invalidate(queryKeys.dashboard)
      invalidate(queryKeys.activityRoot)
      break

    case WS_EVENTS.proposalRiskApproved:
    case WS_EVENTS.proposalRiskRejected:
      invalidateProposal()
      invalidate(queryKeys.riskStatus)
      invalidate(queryKeys.activityRoot)
      break

    case WS_EVENTS.proposalExecutionStarted:
    case WS_EVENTS.proposalExecuted:
    case WS_EVENTS.proposalFailed:
    case WS_EVENTS.proposalCancelled:
      invalidateProposal()
      invalidate(queryKeys.ordersRoot)
      invalidate(queryKeys.portfolio)
      invalidate(queryKeys.positionsRoot)
      invalidate(queryKeys.dashboard)
      invalidate(queryKeys.activityRoot)
      break

    case WS_EVENTS.orderCreated:
    case WS_EVENTS.orderSubmitted:
    case WS_EVENTS.orderPartiallyFilled:
    case WS_EVENTS.orderFilled:
    case WS_EVENTS.orderCancelled:
    case WS_EVENTS.orderRejected:
      invalidate(queryKeys.ordersRoot)
      invalidate(queryKeys.positionsRoot)
      invalidate(queryKeys.portfolio)
      invalidate(queryKeys.dashboard)
      break

    case WS_EVENTS.executionCreated:
      invalidate(queryKeys.ordersRoot)
      invalidate(queryKeys.positionsRoot)
      invalidate(queryKeys.portfolio)
      invalidate(queryKeys.dashboard)
      break

    case WS_EVENTS.tradeCompleted:
      invalidate(queryKeys.trades())
      invalidate(queryKeys.portfolio)
      invalidate(queryKeys.dashboard)
      break

    case WS_EVENTS.portfolioUpdated:
      invalidate(queryKeys.portfolio)
      invalidate(queryKeys.dashboard)
      break

    case WS_EVENTS.positionUpdated:
    case WS_EVENTS.positionCreated:
    case WS_EVENTS.positionClosed:
      invalidate(queryKeys.positionsRoot)
      invalidate(queryKeys.portfolio)
      invalidate(queryKeys.dashboard)
      break

    case WS_EVENTS.strategySignal:
      invalidate(queryKeys.markets)
      invalidate(queryKeys.strategies)
      invalidate(['strategies', 'signals'])
      invalidate(queryKeys.dashboard)
      break

    case WS_EVENTS.strategyEnabled:
    case WS_EVENTS.strategyDisabled:
      invalidate(queryKeys.strategies)
      invalidate(queryKeys.activityRoot)
      break

    case WS_EVENTS.riskWarning:
    case WS_EVENTS.riskCritical:
    case WS_EVENTS.riskEvaluationCreated:
      invalidate(queryKeys.riskStatus)
      invalidate(['risk', 'events'])
      invalidate(queryKeys.dashboard)
      break

    case WS_EVENTS.riskTradingStateChanged:
      invalidate(queryKeys.riskStatus)
      invalidate(queryKeys.riskTrading)
      invalidate(queryKeys.systemStatus)
      invalidate(queryKeys.dashboard)
      invalidate(queryKeys.activityRoot)
      break

    case WS_EVENTS.notificationCreated:
      invalidate(queryKeys.notificationsRoot)
      invalidate(queryKeys.notificationUnread)
      break

    case WS_EVENTS.backtestCreated:
    case WS_EVENTS.backtestStarted:
    case WS_EVENTS.backtestCompleted:
    case WS_EVENTS.backtestFailed:
    case WS_EVENTS.backtestCancelled: {
      invalidate(queryKeys.backtestsRoot)
      const backtestId = typeof data.backtest_id === 'string' ? data.backtest_id : null
      if (backtestId) {
        invalidate(queryKeys.backtest(backtestId))
        invalidate(queryKeys.backtestResult(backtestId))
      }
      break
    }

    case WS_EVENTS.systemStatusChanged:
      invalidate(queryKeys.systemStatus)
      break

    case WS_EVENTS.brokerConnected:
    case WS_EVENTS.brokerDisconnected:
      invalidate(queryKeys.health)
      break

    case WS_EVENTS.quoteUpdated:
      invalidate(queryKeys.markets)
      break

    default:
      // Unknown/future events are ignored for cache purposes but still
      // observable via `useWebSocket().onEvent`.
      break
  }
}
