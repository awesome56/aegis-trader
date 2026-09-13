import type { PageParams, Paginated } from '~/types/api'
import type { Trade, TradeDetail } from '~/types/trade'
import { api } from './client'
import { isMockEnabled } from './config'
import { toTradeDetail, toTradePage } from './adapters'
import type { RawTrade, RawTradePage } from './adapters/raw'
import { mockTrade, mockTrades } from '~/mocks'

function query(params: PageParams): Record<string, unknown> {
  const page = Number(params.page ?? 1)
  const pageSize = Number(params.pageSize ?? params.limit ?? 50)
  const result: Record<string, unknown> = { page, page_size: pageSize }
  if (params.symbol) result.symbol = String(params.symbol).trim().toUpperCase()
  return result
}

export const tradesService = {
  list: async (params: PageParams = {}): Promise<Paginated<Trade>> => {
    if (isMockEnabled()) {
      const items = mockTrades()
      return { items, total: items.length, page: 1, pageSize: items.length || 1 }
    }
    return toTradePage(await api.get<RawTradePage>('/trades', { query: query(params) }))
  },
  get: async (id: string): Promise<TradeDetail> => {
    if (isMockEnabled()) {
      const detail = mockTrade(id)
      if (!detail) throw new Error(`Trade ${id} not found (mock)`)
      return detail
    }
    return toTradeDetail(await api.get<RawTrade>(`/trades/${id}`))
  },
}
