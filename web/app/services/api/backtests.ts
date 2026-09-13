import type { PageParams, Paginated } from '~/types/api'
import type { Backtest, BacktestConfig, BacktestResult } from '~/types/backtest'
import { api } from './client'
import { isMockEnabled } from './config'
import { toBacktest, toBacktestPage, toBacktestResult } from './adapters'
import type { RawBacktest, RawBacktestPage, RawBacktestResult } from './adapters/raw'
import { mockBacktestResult, mockBacktests } from '~/mocks'

/**
 * Backtests run entirely on the backend using the production strategy
 * implementations. The browser only submits configuration and displays results.
 */
export const backtestsService = {
  list: async (params: PageParams = {}): Promise<Paginated<Backtest>> => {
    if (isMockEnabled()) {
      const items = mockBacktests()
      return { items, total: items.length, page: 1, pageSize: items.length || 1 }
    }
    const page = Number(params.page ?? 1)
    const pageSize = Number(params.pageSize ?? 25)
    return toBacktestPage(
      await api.get<RawBacktestPage>('/backtests', { query: { page, page_size: pageSize } }),
    )
  },
  get: async (id: string): Promise<Backtest> => {
    if (isMockEnabled()) {
      const found = mockBacktests().find((backtest) => backtest.id === id)
      if (!found) throw new Error(`Backtest ${id} not found (mock)`)
      return found
    }
    return toBacktest(await api.get<RawBacktest>(`/backtests/${id}`))
  },
  run: async (config: BacktestConfig): Promise<Backtest> => {
    if (isMockEnabled()) {
      const items = mockBacktests()
      const first = items[0]
      if (!first) throw new Error('No mock backtests available')
      return first
    }
    return toBacktest(await api.post<RawBacktest>('/backtests', config))
  },
  result: async (id: string): Promise<BacktestResult> => {
    if (isMockEnabled()) {
      const result = mockBacktestResult(id)
      if (!result) throw new Error(`Backtest ${id} has no result (mock)`)
      return result
    }
    return toBacktestResult(await api.get<RawBacktestResult>(`/backtests/${id}/result`))
  },
  cancel: async (id: string): Promise<Backtest> => {
    if (isMockEnabled()) throw new Error('Backtest cancellation is unavailable in mock mode')
    return toBacktest(await api.post<RawBacktest>(`/backtests/${id}/cancel`))
  },
}
