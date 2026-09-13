import type { PageParams } from '~/types/api'
import type { PortfolioRange } from '~/types/portfolio'
import type { CandleTimeframe } from '~/types/market'

/**
 * Central TanStack Query key factory. Keeping keys in one place makes targeted
 * WebSocket cache invalidation reliable and avoids stringly-typed drift.
 */
export const queryKeys = {
  dashboard: ['dashboard'] as const,

  portfolio: ['portfolio'] as const,
  portfolioHistory: (range: PortfolioRange) => ['portfolio', 'history', range] as const,
  allocation: ['portfolio', 'allocation'] as const,

  positionsRoot: ['positions'] as const,
  positions: (params: PageParams = {}) => ['positions', params] as const,
  position: (id: string) => ['positions', id] as const,

  markets: ['markets'] as const,
  marketSearch: (query: string) => ['markets', 'search', query] as const,
  asset: (symbol: string) => ['markets', symbol] as const,
  candles: (symbol: string, timeframe: CandleTimeframe) =>
    ['markets', symbol, 'candles', timeframe] as const,

  trades: (params: PageParams = {}) => ['trades', params] as const,
  trade: (id: string) => ['trades', id] as const,

  ordersRoot: ['orders'] as const,
  orders: (params: PageParams = {}) => ['orders', params] as const,
  order: (id: string) => ['orders', id] as const,

  agentStatus: ['agent', 'status'] as const,
  agentRunsRoot: ['agent', 'runs'] as const,
  agentRuns: (params: PageParams = {}) => ['agent', 'runs', params] as const,
  agentRun: (id: string) => ['agent', 'runs', id] as const,
  agentDecisionsRoot: ['agent', 'decisions'] as const,
  agentDecisions: (params: PageParams = {}) => ['agent', 'decisions', params] as const,
  agentDecision: (id: string) => ['agent', 'decisions', id] as const,

  aiProviders: ['ai', 'providers'] as const,
  aiProviderCatalog: ['ai', 'providers', 'supported'] as const,

  brokerConnections: ['brokers', 'connections'] as const,
  autoTradingStatus: ['auto-trading', 'status'] as const,
  autoTradingPolicy: (accountId: string) => ['auto-trading', accountId, 'policy'] as const,
  proposalsRoot: ['proposals'] as const,
  proposals: (params: PageParams = {}) => ['proposals', params] as const,
  proposal: (id: string) => ['proposals', id] as const,

  riskStatus: ['risk'] as const,
  riskLimits: ['risk', 'limits'] as const,
  riskSettings: ['risk', 'settings'] as const,
  riskTrading: ['risk', 'trading'] as const,
  riskEvents: (params: PageParams = {}) => ['risk', 'events', params] as const,

  strategies: ['strategies'] as const,
  strategy: (id: string) => ['strategies', id] as const,
  strategySignals: (params: PageParams = {}) => ['strategies', 'signals', params] as const,

  backtests: (params: PageParams = {}) => ['backtests', params] as const,
  backtestsRoot: ['backtests'] as const,
  backtest: (id: string) => ['backtests', id] as const,
  backtestResult: (id: string) => ['backtests', id, 'result'] as const,

  activityRoot: ['activity'] as const,
  activity: (params: PageParams = {}) => ['activity', params] as const,

  notificationsRoot: ['notifications'] as const,
  notifications: (params: PageParams = {}) => ['notifications', params] as const,
  notificationUnread: ['notifications', 'unread'] as const,

  systemStatus: ['system', 'status'] as const,
  health: ['system', 'health'] as const,
} as const
