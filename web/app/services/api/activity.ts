import type { PageParams, Paginated } from '~/types/api'
import type { ActivityEvent } from '~/types/activity'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockActivity } from '~/mocks'

/** BACKEND REQUIREMENT: `GET /activity` (not yet implemented). */
export const activityService = {
  list: async (params: PageParams = {}): Promise<Paginated<ActivityEvent>> => {
    if (isMockEnabled()) {
      const items = mockActivity()
      return { items, total: items.length, page: 1, pageSize: items.length }
    }
    return api.get<Paginated<ActivityEvent>>('/activity', { query: params })
  },
}
