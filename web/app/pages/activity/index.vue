<script setup lang="ts">
import type { ActivitySeverity } from '~/types/activity'
import { useActivity } from '~/composables/useActivity'
import { formatDateTime } from '~/utils/dates'

useHead({ title: 'Activity' })

const source = ref('')
const severity = ref<ActivitySeverity | ''>('')
const eventType = ref('')
const start = ref('')
const end = ref('')
const page = ref(1)
const pageSize = 50

const params = computed(() => ({
  page: page.value,
  pageSize,
  source: source.value.trim() || undefined,
  severity: severity.value || undefined,
  event_type: eventType.value.trim() || undefined,
  start: start.value ? new Date(start.value).toISOString() : undefined,
  end: end.value ? new Date(`${end.value}T23:59:59`).toISOString() : undefined,
}))

const activityQuery = useActivity(params)
const items = computed(() => activityQuery.data.value?.items ?? [])
const total = computed(() => activityQuery.data.value?.total ?? 0)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

watch([source, severity, eventType, start, end], () => {
  page.value = 1
})

const expanded = ref<Record<string, boolean>>({})
function toggle(id: string): void {
  expanded.value = { ...expanded.value, [id]: !expanded.value[id] }
}

function metadataRows(data: Record<string, unknown> | null): { key: string; value: string }[] {
  if (!data) return []
  return Object.entries(data).map(([key, value]) => ({
    key,
    value: typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value),
  }))
}
</script>

<template>
  <div>
    <PageHeader title="Activity" subtitle="Complete audit trail across the platform." eyebrow="Audit">
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="activityQuery.isLoading.value" @click="activityQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <div class="mb-3 flex flex-wrap items-end gap-2">
      <div>
        <label class="mb-1 block text-[11px] text-muted" for="act-source">Component</label>
        <UInput id="act-source" v-model="source" placeholder="risk, broker…" class="w-36" />
      </div>
      <div>
        <label class="mb-1 block text-[11px] text-muted" for="act-severity">Severity</label>
        <select id="act-severity" v-model="severity" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
          <option value="">All</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
      </div>
      <div>
        <label class="mb-1 block text-[11px] text-muted" for="act-event">Event type</label>
        <UInput id="act-event" v-model="eventType" placeholder="proposal, order…" class="w-40" />
      </div>
      <div>
        <label class="mb-1 block text-[11px] text-muted" for="act-start">From</label>
        <input id="act-start" v-model="start" type="date" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default" />
      </div>
      <div>
        <label class="mb-1 block text-[11px] text-muted" for="act-end">To</label>
        <input id="act-end" v-model="end" type="date" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default" />
      </div>
      <span class="ml-auto self-center text-[11px] text-muted">{{ total }} events</span>
    </div>

    <ErrorState
      v-if="activityQuery.isError.value"
      title="Activity unavailable"
      message="The activity API did not respond. Check the backend connection and retry."
      @retry="activityQuery.refetch()"
    />

    <div v-else class="rounded-lg border border-default bg-elevated/30 p-4">
      <LoadingSkeleton v-if="activityQuery.isLoading.value" :rows="6" />
      <div v-else-if="items.length" class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="text-muted">
            <tr>
              <th class="pb-2 font-medium">Time</th>
              <th class="pb-2 font-medium">Component</th>
              <th class="pb-2 font-medium">Severity</th>
              <th class="pb-2 font-medium">Env</th>
              <th class="pb-2 font-medium">Event</th>
              <th class="pb-2 font-medium">Symbol</th>
              <th class="pb-2 font-medium">Message</th>
              <th class="pb-2 text-right font-medium"></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="event in items" :key="event.id">
              <tr class="border-t border-default hover:bg-elevated/40">
                <td class="py-2 text-muted">{{ formatDateTime(event.occurred_at) }}</td>
                <td class="py-2 text-default">{{ event.component }}</td>
                <td class="py-2">
                  <StatusBadge
                    :label="event.severity"
                    :tone="event.severity === 'CRITICAL' ? 'danger' : event.severity === 'WARNING' ? 'warning' : 'info'"
                  />
                </td>
                <td class="py-2">
                  <EnvironmentBadge :environment="event.environment" />
                  <span v-if="!event.environment" class="text-muted">—</span>
                </td>
                <td class="num py-2 text-muted">{{ event.event_type }}</td>
                <td class="py-2">
                  <SymbolBadge v-if="event.symbol" :symbol="event.symbol" size="sm" />
                  <span v-else class="text-muted">—</span>
                </td>
                <td class="max-w-md py-2 text-default">{{ event.message }}</td>
                <td class="py-2 text-right">
                  <div class="flex justify-end gap-1">
                    <UButton v-if="event.link" color="neutral" variant="ghost" size="xs" :to="event.link">Open</UButton>
                    <UButton
                      v-if="event.data"
                      color="neutral"
                      variant="ghost"
                      size="xs"
                      @click="toggle(event.id)"
                    >
                      Details
                    </UButton>
                  </div>
                </td>
              </tr>
              <tr v-if="expanded[event.id]" class="border-t border-default">
                <td colspan="8" class="bg-elevated/10 p-3">
                  <table v-if="metadataRows(event.data).length" class="w-full max-w-lg text-left text-[11px]">
                    <tbody>
                      <tr v-for="row in metadataRows(event.data)" :key="row.key" class="border-t border-default first:border-t-0">
                        <td class="py-1 pr-4 text-muted">{{ row.key }}</td>
                        <td class="num py-1 text-default">{{ row.value }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <p v-else class="text-[11px] text-muted">No structured metadata.</p>
                  <p v-if="event.actor" class="mt-2 text-[11px] text-muted">Actor: {{ event.actor }}</p>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <EmptyState
        v-else
        title="No activity"
        message="No audit events matched the current filters."
        icon="i-lucide-activity"
      />

      <div v-if="pageCount > 1" class="mt-3 flex items-center justify-between text-xs text-muted">
        <span>Page {{ page }} of {{ pageCount }}</span>
        <div class="flex gap-1">
          <UButton color="neutral" variant="outline" size="xs" :disabled="page <= 1" @click="page -= 1">Prev</UButton>
          <UButton color="neutral" variant="outline" size="xs" :disabled="page >= pageCount" @click="page += 1">Next</UButton>
        </div>
      </div>
    </div>
  </div>
</template>
