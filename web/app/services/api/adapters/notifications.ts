import type { Notification, NotificationPage, NotificationSeverity } from '~/types/notifications'
import { resourceLinkFromPayload } from '~/utils/resourceLinks'
import { iso, isoOrNull, normalizeEnvironment } from './common'
import type { RawNotification, RawNotificationPage } from './raw'

export function toNotification(raw: RawNotification): Notification {
  return {
    id: raw.id,
    category: raw.category,
    severity: raw.severity as NotificationSeverity,
    title: raw.title,
    message: raw.message,
    is_read: raw.is_read,
    read_at: isoOrNull(raw.read_at),
    payload: raw.payload,
    created_at: iso(raw.created_at),
    link: resourceLinkFromPayload(raw.payload),
    environment: normalizeEnvironment(raw.payload),
  }
}

export function toNotificationPage(raw: RawNotificationPage): NotificationPage {
  return {
    items: raw.items.map(toNotification),
    total: raw.total,
    page: raw.page,
    pageSize: raw.page_size,
  }
}
