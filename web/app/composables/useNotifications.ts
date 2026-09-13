import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { notificationsService } from '~/services/api/notifications'
import type { PageParams } from '~/types/api'
import type { NotificationPage } from '~/types/notifications'

export function useNotificationList(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<NotificationPage>({
    queryKey: computed(() => queryKeys.notifications(toValue(params))),
    queryFn: () => notificationsService.list(toValue(params)),
    staleTime: 10_000,
  })
}

export function useNotificationUnreadCount() {
  return useQuery<number>({
    queryKey: queryKeys.notificationUnread,
    queryFn: () => notificationsService.unreadCount(),
    staleTime: 10_000,
  })
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => notificationsService.markRead(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.notificationsRoot })
      void queryClient.invalidateQueries({ queryKey: queryKeys.notificationUnread })
    },
  })
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => notificationsService.markAllRead(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.notificationsRoot })
      void queryClient.invalidateQueries({ queryKey: queryKeys.notificationUnread })
    },
  })
}

/** Backend notification centre access (list, unread count, read mutations). */
export function useNotifications() {
  const listQuery = useNotificationList({ page: 1, pageSize: 10 })
  const unreadQuery = useNotificationUnreadCount()
  const markRead = useMarkNotificationRead()
  const markAllRead = useMarkAllNotificationsRead()

  return {
    listQuery,
    unreadQuery,
    unreadCount: computed(() => unreadQuery.data.value ?? 0),
    items: computed(() => listQuery.data.value?.items ?? []),
    markRead,
    markAllRead,
  }
}
