import { storeToRefs } from 'pinia'
import { useNotificationsStore } from '~/stores/notifications'
import type { AppNotification } from '~/types/notifications'

/** In-app notification centre access. */
export function useNotifications() {
  const store = useNotificationsStore()
  const { items, unreadCount } = storeToRefs(store)

  return {
    items,
    unreadCount,
    markRead: (id: string) => store.markRead(id),
    markAllRead: () => store.markAllRead(),
    remove: (id: string) => store.remove(id),
    clear: () => store.clear(),
    push: (notification: Omit<AppNotification, 'id' | 'created_at' | 'read'>) =>
      store.push(notification),
  }
}
