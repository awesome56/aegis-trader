import type { PageParams, Paginated } from '~/types/api'
import type { ActivityEvent } from '~/types/activity'
import { api } from './client'
import { isMockEnabled } from './config'
import { toActivityPage } from './adapters'
import type { RawActivityPage } from './adapters/raw'
import { mockActivity } from '~/mocks'

function query(params: PageParams): Record<string, unknown> {
  const page = Number(params.page ?? 1)
  const pageSize = Number(params.pageSize ?? params.limit ?? 50)
  const result: Record<string, unknown> = { page, page_size: pageSize }
  for (const key of ['source', 'severity', 'event_type', 'start', 'end']) {
    const value = params[key]
    if (value !== undefined && value !== '') result[key] = value
  }
  return result
}

export const activityService = {
  list: async (params: PageParams = {}): Promise<Paginated<ActivityEvent>> => {
    if (isMockEnabled()) {
      const items = mockActivity()
      return { items, total: items.length, page: 1, pageSize: items.length || 1 }
    }
    return toActivityPage(await api.get<RawActivityPage>('/activity', { query: query(params) }))
  },
}
