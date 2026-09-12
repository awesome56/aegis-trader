import type { PageParams, Paginated } from '~/types/api'
import type { Backtest, BacktestConfig, BacktestResult } from '~/types/backtest'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockBacktestResult, mockBacktests } from '~/mocks'

/**
 * BACKEND REQUIREMENT (not yet implemented):
 *   GET /backtests
 *   POST /backtests
 *   GET /backtests/{id}
 *
 * All backtest computation happens on the backend using the production
 * strategy implementations. The browser only submits configuration and
 * displays the returned result.
 */
export const backtestsService = {
  list: async (params: PageParams = {}): Promise<Paginated<Backtest>> => {
    if (isMockEnabled()) {
      const items = mockBacktests()
      return { items, total: items.length, page: 1, pageSize: items.length }
    }
    return api.get<Paginated<Backtest>>('/backtests', { query: params })
  },
  get: async (id: string): Promise<Backtest> => {
    if (isMockEnabled()) {
      const found = mockBacktests().find((backtest) => backtest.id === id)
      if (!found) throw new Error(`Backtest ${id} not found (mock)`)
      return found
    }
    return api.get<Backtest>(`/backtests/${id}`)
  },
  run: async (config: BacktestConfig): Promise<Backtest> => {
    if (isMockEnabled()) {
      const created: Backtest = {
        id: `bt-${Date.now()}`,
        name: `${config.symbols.join(', ')} backtest`,
        strategy_id: config.strategy_id,
        strategy_name: null,
        symbols: config.symbols,
        timeframe: config.timeframe,
        start_date: config.start_date,
        end_date: config.end_date,
        initial_capital: config.initial_capital,
        status: 'RUNNING',
        created_at: new Date().toISOString(),
        completed_at: null,
        error: null,
      }
      return created
    }
    return api.post<Backtest>('/backtests', config)
  },
  result: async (id: string): Promise<BacktestResult> => {
    if (isMockEnabled()) {
      const result = mockBacktestResult(id)
      if (!result) throw new Error(`Backtest ${id} has no result (mock)`)
      return result
    }
    return api.get<BacktestResult>(`/backtests/${id}/result`)
  },
}
