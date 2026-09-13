import type { PageParams, Paginated } from '~/types/api'
import type { Order, OrderDetail } from '~/types/order'
import { api } from './client'
import { isMockEnabled } from './config'
import { toOrderDetail, toOrderList } from './adapters'
import type { RawBrokerOrder, RawBrokerOrderList } from './adapters/raw'
import { mockOrder, mockOrders } from '~/mocks'

export const ordersService = {
  list: async (params: PageParams = {}): Promise<Paginated<Order>> => {
    if (isMockEnabled()) {
      const items = mockOrders()
      return { items, total: items.length, page: 1, pageSize: items.length || 1 }
    }
    const limit = Number(params.limit ?? params.pageSize ?? 50)
    const page = Number(params.page ?? 1)
    const offset = Number(params.offset ?? (page - 1) * limit)
    const query: Record<string, unknown> = { limit, offset }
    if (params.status) query.status = params.status
    return toOrderList(await api.get<RawBrokerOrderList>('/broker/orders', { query }))
  },
  get: async (id: string): Promise<OrderDetail> => {
    if (isMockEnabled()) {
      const detail = mockOrder(id)
      if (!detail) throw new Error(`Order ${id} not found (mock)`)
      return detail
    }
    return toOrderDetail(await api.get<RawBrokerOrder>(`/broker/orders/${id}`))
  },
  cancel: async (id: string): Promise<OrderDetail> => {
    if (isMockEnabled()) throw new Error('Order cancellation is unavailable in mock mode')
    return toOrderDetail(await api.delete<RawBrokerOrder>(`/broker/orders/${id}`))
  },
}
