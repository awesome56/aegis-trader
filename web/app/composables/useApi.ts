import {
  activityService,
  agentService,
  ApiError,
  authService,
  backtestsService,
  dashboardService,
  marketsService,
  ordersService,
  portfolioService,
  positionsService,
  riskService,
  strategiesService,
  systemService,
  tradesService,
} from '~/services/api'

const api = {
  activity: activityService,
  agent: agentService,
  auth: authService,
  backtests: backtestsService,
  dashboard: dashboardService,
  markets: marketsService,
  orders: ordersService,
  portfolio: portfolioService,
  positions: positionsService,
  risk: riskService,
  strategies: strategiesService,
  system: systemService,
  trades: tradesService,
} as const

/**
 * Access the API service layer. Components should never build URLs directly —
 * they call these services (usually through a feature composable).
 */
export function useApi() {
  return api
}

export { ApiError }
