import type { PageParams, Paginated } from '~/types/api'
import type { Trade, TradeDetail } from '~/types/trade'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockTrade, mockTrades } from '~/mocks'

/** BACKEND REQUIREMENT: `GET /trades`, `GET /trades/{id}` (not yet implemented). */
export const tradesService = {
  list: async (params: PageParams = {}): Promise<Paginated<Trade>> => {
    if (isMockEnabled()) {
      const items = mockTrades()
      return { items, total: items.length, page: 1, pageSize: items.length }
    }
    return api.get<Paginated<Trade>>('/trades', { query: params })
  },
  get: async (id: string): Promise<TradeDetail> => {
    if (isMockEnabled()) {
      const detail = mockTrade(id)
      if (!detail) throw new Error(`Trade ${id} not found (mock)`)
      return detail
    }
    return api.get<TradeDetail>(`/trades/${id}`)
  },
}
