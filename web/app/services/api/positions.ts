import type { PageParams, Paginated } from '~/types/api'
import type { Position, PositionDetail } from '~/types/position'
import { api } from './client'
import { isMockEnabled } from './config'
import { toPosition, toPositionDetail } from './adapters'
import type { RawPositionValuation } from './adapters/raw'
import { mockPosition, mockPositions } from '~/mocks'

export const positionsService = {
  list: async (_params: PageParams = {}): Promise<Paginated<Position>> => {
    if (isMockEnabled()) {
      const items = mockPositions()
      return { items, total: items.length, page: 1, pageSize: items.length }
    }
    const raw = await api.get<RawPositionValuation[]>('/positions')
    const items = raw.map(toPosition)
    return { items, total: items.length, page: 1, pageSize: items.length || 1 }
  },
  get: async (id: string): Promise<PositionDetail> => {
    if (isMockEnabled()) {
      const detail = mockPosition(id)
      if (!detail) throw new Error(`Position ${id} not found (mock)`)
      return detail
    }
    return toPositionDetail(await api.get<RawPositionValuation>(`/positions/${id}`))
  },
}
