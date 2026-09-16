import type { ActivityEvent, ActivitySeverity } from '~/types/activity'
import type { Paginated } from '~/types/api'
import { resourceLinkFromPayload } from '~/utils/resourceLinks'
import { iso, normalizeEnvironment } from './common'
import type { RawActivityEvent, RawActivityPage } from './raw'

export function toActivityEvent(raw: RawActivityEvent): ActivityEvent {
  return {
    id: raw.id,
    component: raw.source,
    event_type: raw.event_type,
    severity: raw.severity as ActivitySeverity,
    message: raw.message,
    symbol: typeof raw.payload?.symbol === 'string' ? raw.payload.symbol : null,
    actor: raw.actor,
    correlation_id: raw.correlation_id,
    data: raw.payload,
    occurred_at: iso(raw.occurred_at),
    link: resourceLinkFromPayload(raw.payload),
    environment: normalizeEnvironment(raw.payload),
  }
}

export function toActivityPage(raw: RawActivityPage): Paginated<ActivityEvent> {
  return {
    items: raw.items.map(toActivityEvent),
    total: raw.total,
    page: raw.page,
    pageSize: raw.page_size,
  }
}
