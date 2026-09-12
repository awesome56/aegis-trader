import type { PageParams, Paginated } from '~/types/api'
import type { Order, OrderDetail } from '~/types/order'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockOrder, mockOrders } from '~/mocks'

/**
 * BACKEND REQUIREMENT: `GET /orders`, `GET /orders/{id}` (not yet implemented).
 * The order lifecycle is read-only from the browser — the frontend never
 * submits or cancels orders directly.
 */
export const ordersService = {
  list: async (params: PageParams = {}): Promise<Paginated<Order>> => {
    if (isMockEnabled()) {
      const items = mockOrders()
      return { items, total: items.length, page: 1, pageSize: items.length }
    }
    return api.get<Paginated<Order>>('/orders', { query: params })
  },
  get: async (id: string): Promise<OrderDetail> => {
    if (isMockEnabled()) {
      const detail = mockOrder(id)
      if (!detail) throw new Error(`Order ${id} not found (mock)`)
      return detail
    }
    return api.get<OrderDetail>(`/orders/${id}`)
  },
}
