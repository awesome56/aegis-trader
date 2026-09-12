import type { PageParams, Paginated } from '~/types/api'
import type { Position, PositionDetail } from '~/types/position'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockPosition, mockPositions } from '~/mocks'

/** BACKEND REQUIREMENT: `GET /positions`, `GET /positions/{id}` (not yet implemented). */
export const positionsService = {
  list: async (params: PageParams = {}): Promise<Paginated<Position>> => {
    if (isMockEnabled()) {
      const items = mockPositions()
      return { items, total: items.length, page: 1, pageSize: items.length }
    }
    return api.get<Paginated<Position>>('/positions', { query: params })
  },
  get: async (id: string): Promise<PositionDetail> => {
    if (isMockEnabled()) {
      const detail = mockPosition(id)
      if (!detail) throw new Error(`Position ${id} not found (mock)`)
      return detail
    }
    return api.get<PositionDetail>(`/positions/${id}`)
  },
}
