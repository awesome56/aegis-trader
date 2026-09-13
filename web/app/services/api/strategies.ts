import type { PageParams } from '~/types/api'
import type {
  Strategy,
  StrategyDetail,
  StrategyEvaluation,
  StrategySignalPage,
} from '~/types/strategy'
import { api } from './client'
import { isMockEnabled } from './config'
import {
  toStrategy,
  toStrategyDetail,
  toStrategyEvaluation,
  toStrategySignalPage,
} from './adapters'
import type {
  RawSignalPage,
  RawStrategy,
  RawStrategyDetail,
  RawStrategyEvaluation,
} from './adapters/raw'
import { mockStrategies, mockStrategy, mockSignals } from '~/mocks'

export interface EvaluateStrategyInput {
  symbol: string
  timeframe?: string
  strategy_ids?: string[]
}

function signalQuery(params: PageParams): Record<string, unknown> {
  const pageSize = Number(params.pageSize ?? params.limit ?? 50)
  const page = Number(params.page ?? 1)
  const query: Record<string, unknown> = { page, page_size: pageSize }
  for (const key of ['strategy_id', 'symbol', 'timeframe', 'direction', 'start', 'end']) {
    const value = params[key]
    if (value !== undefined && value !== '') query[key] = value
  }
  return query
}

export const strategiesService = {
  list: async (): Promise<Strategy[]> => {
    if (isMockEnabled()) return mockStrategies()
    return (await api.get<RawStrategy[]>('/strategies')).map(toStrategy)
  },
  get: async (id: string): Promise<StrategyDetail> => {
    if (isMockEnabled()) {
      const detail = mockStrategy(id)
      if (!detail) throw new Error(`Strategy ${id} not found (mock)`)
      return detail
    }
    return toStrategyDetail(await api.get<RawStrategyDetail>(`/strategies/${id}`))
  },
  signals: async (params: PageParams = {}): Promise<StrategySignalPage> => {
    if (isMockEnabled()) {
      const items = mockSignals()
      return { items, total: items.length, page: 1, pageSize: items.length || 1 }
    }
    return toStrategySignalPage(
      await api.get<RawSignalPage>('/strategies/signals', { query: signalQuery(params) }),
    )
  },
  strategySignals: async (id: string, params: PageParams = {}): Promise<StrategySignalPage> => {
    if (isMockEnabled()) {
      const items = mockSignals().filter((signal) => signal.strategy_id === id)
      return { items, total: items.length, page: 1, pageSize: items.length || 1 }
    }
    return toStrategySignalPage(
      await api.get<RawSignalPage>(`/strategies/${id}/signals`, { query: signalQuery(params) }),
    )
  },
  enable: async (id: string): Promise<Strategy> => {
    if (isMockEnabled()) throw new Error('Strategy enable is unavailable in mock mode')
    return toStrategy(await api.post<RawStrategy>(`/strategies/${id}/enable`))
  },
  disable: async (id: string): Promise<Strategy> => {
    if (isMockEnabled()) throw new Error('Strategy disable is unavailable in mock mode')
    return toStrategy(await api.post<RawStrategy>(`/strategies/${id}/disable`))
  },
  evaluate: async (input: EvaluateStrategyInput): Promise<StrategyEvaluation[]> => {
    if (isMockEnabled()) return []
    return (
      await api.post<RawStrategyEvaluation[]>('/strategies/evaluate', {
        symbol: input.symbol,
        timeframe: input.timeframe,
        strategy_ids: input.strategy_ids,
      })
    ).map(toStrategyEvaluation)
  },
}
