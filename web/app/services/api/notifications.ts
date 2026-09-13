import type { PageParams } from '~/types/api'
import type { Notification, NotificationPage } from '~/types/notifications'
import { api } from './client'
import { isMockEnabled } from './config'
import { toNotification, toNotificationPage } from './adapters'
import type { RawNotification, RawNotificationPage, RawUnreadCount } from './adapters/raw'

function listQuery(params: PageParams): Record<string, unknown> {
  const page = Number(params.page ?? 1)
  const pageSize = Number(params.pageSize ?? params.limit ?? 25)
  const query: Record<string, unknown> = { page, page_size: pageSize }
  if (params.unread_only !== undefined) query.unread_only = params.unread_only
  return query
}

export const notificationsService = {
  list: async (params: PageParams = {}): Promise<NotificationPage> => {
    if (isMockEnabled()) return { items: [], total: 0, page: 1, pageSize: 0 }
    return toNotificationPage(
      await api.get<RawNotificationPage>('/notifications', { query: listQuery(params) }),
    )
  },
  unreadCount: async (): Promise<number> => {
    if (isMockEnabled()) return 0
    return (await api.get<RawUnreadCount>('/notifications/unread-count')).unread
  },
  markRead: async (id: string): Promise<Notification> => {
    if (isMockEnabled()) throw new Error('Notification updates are unavailable in mock mode')
    return toNotification(await api.post<RawNotification>(`/notifications/${id}/read`))
  },
  markAllRead: async (): Promise<number> => {
    if (isMockEnabled()) return 0
    return (await api.post<RawUnreadCount>('/notifications/read-all')).unread
  },
}
