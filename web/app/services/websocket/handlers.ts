import type { QueryClient } from '@tanstack/vue-query'
import type { AnyTradingEvent } from '~/types/websocket'
import { WS_EVENTS } from '~/types/websocket'
import { queryKeys } from '../api/keys'

/**
 * Route incoming WebSocket events to targeted TanStack Query cache updates.
 *
 * We invalidate only the queries each event can affect (never the whole app),
 * and patch cheap, high-frequency values directly.
 */
export function applyEventToCache(queryClient: QueryClient, event: AnyTradingEvent): void {
  const invalidate = (queryKey: readonly unknown[]) =>
    void queryClient.invalidateQueries({ queryKey })

  switch (event.event) {
    case WS_EVENTS.orderFilled:
    case WS_EVENTS.orderPartiallyFilled:
    case WS_EVENTS.orderSubmitted:
    case WS_EVENTS.orderCancelled:
    case WS_EVENTS.orderFailed:
    case WS_EVENTS.orderCreated:
      invalidate(queryKeys.orders())
      invalidate(queryKeys.positions())
      invalidate(queryKeys.portfolio)
      invalidate(queryKeys.trades())
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
      invalidate(queryKeys.positions())
      invalidate(queryKeys.portfolio)
      invalidate(queryKeys.dashboard)
      break

    case WS_EVENTS.proposalCreated:
    case WS_EVENTS.proposalApproved:
    case WS_EVENTS.proposalRejected:
      invalidate(queryKeys.proposals())
      invalidate(queryKeys.decisions())
      invalidate(queryKeys.agentStatus)
      invalidate(queryKeys.dashboard)
      break

    case WS_EVENTS.agentStarted:
    case WS_EVENTS.agentAssetAnalysis:
    case WS_EVENTS.agentCompleted:
      invalidate(queryKeys.agentStatus)
      invalidate(queryKeys.decisions())
      break

    case WS_EVENTS.strategySignal:
      invalidate(queryKeys.markets)
      invalidate(queryKeys.strategies)
      break

    case WS_EVENTS.riskWarning:
    case WS_EVENTS.riskCritical:
      invalidate(queryKeys.riskStatus)
      invalidate(queryKeys.riskEvents())
      invalidate(queryKeys.dashboard)
      break

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
