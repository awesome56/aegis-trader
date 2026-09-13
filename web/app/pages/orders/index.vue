<script setup lang="ts">
import type { OrderStatus } from '~/types/order'
import { useOrders } from '~/composables/useOrders'
import { formatCurrency } from '~/utils/currency'
import { formatDateTime } from '~/utils/dates'

useHead({ title: 'Orders' })

const TABS: { key: string; label: string; status: OrderStatus | '' }[] = [
  { key: 'all', label: 'All', status: '' },
  { key: 'created', label: 'Created', status: 'CREATED' },
  { key: 'submitted', label: 'Submitted', status: 'SUBMITTED' },
  { key: 'partial', label: 'Partially Filled', status: 'PARTIALLY_FILLED' },
  { key: 'filled', label: 'Filled', status: 'FILLED' },
  { key: 'cancelled', label: 'Cancelled', status: 'CANCELLED' },
  { key: 'rejected', label: 'Rejected', status: 'REJECTED' },
]

const tab = ref('all')
const page = ref(1)
const pageSize = 50
const statusFilter = computed(() => TABS.find((entry) => entry.key === tab.value)?.status ?? '')

const params = computed(() => ({
  page: page.value,
  pageSize,
  status: statusFilter.value || undefined,
}))

const ordersQuery = useOrders(params)
const items = computed(() => ordersQuery.data.value?.items ?? [])
const total = computed(() => ordersQuery.data.value?.total ?? 0)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

watch(tab, () => {
  page.value = 1
})

const tone: Record<string, 'neutral' | 'info' | 'success' | 'warning' | 'danger'> = {
  BUY: 'success',
  SELL: 'danger',
}
</script>

<template>
  <div>
    <PageHeader title="Orders" subtitle="Paper broker order lifecycle — view and cancel resting orders." eyebrow="Trading">
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="ordersQuery.isLoading.value" @click="ordersQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <div class="mb-3 flex flex-wrap gap-1">
      <button
        v-for="entry in TABS"
        :key="entry.key"
        type="button"
        class="rounded border px-2.5 py-1 text-xs font-medium transition-colors"
        :class="tab === entry.key ? 'border-accented bg-elevated text-highlighted' : 'border-default text-muted hover:text-default'"
        @click="tab = entry.key"
      >
        {{ entry.label }}
      </button>
      <span class="ml-auto self-center text-[11px] text-muted">{{ total }} orders</span>
    </div>

    <ErrorState
      v-if="ordersQuery.isError.value"
      title="Orders unavailable"
      message="The broker orders API did not respond. Check the backend connection and retry."
      @retry="ordersQuery.refetch()"
    />

    <div v-else class="rounded-lg border border-default bg-elevated/30 p-4">
      <LoadingSkeleton v-if="ordersQuery.isLoading.value" :rows="6" />
      <div v-else-if="items.length" class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="text-muted">
            <tr>
              <th class="pb-2 font-medium">Order</th>
              <th class="pb-2 font-medium">Created</th>
              <th class="pb-2 font-medium">Symbol</th>
              <th class="pb-2 font-medium">Side</th>
              <th class="pb-2 font-medium">Type</th>
              <th class="pb-2 text-right font-medium">Qty</th>
              <th class="pb-2 text-right font-medium">Filled</th>
              <th class="pb-2 text-right font-medium">Remaining</th>
              <th class="pb-2 text-right font-medium">Limit</th>
              <th class="pb-2 text-right font-medium">Avg fill</th>
              <th class="pb-2 text-right font-medium">Fees</th>
              <th class="pb-2 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in items" :key="order.id" class="border-t border-default hover:bg-elevated/40">
              <td class="py-2">
                <NuxtLink :to="`/orders/${order.id}`" class="num text-muted hover:underline">
                  {{ order.id.slice(0, 8) }}
                </NuxtLink>
              </td>
              <td class="py-2 text-muted">{{ formatDateTime(order.created_at) }}</td>
              <td class="py-2"><SymbolBadge :symbol="order.symbol" size="sm" /></td>
              <td class="py-2"><StatusBadge :label="order.side" :tone="tone[order.side]" /></td>
              <td class="py-2 text-muted">{{ order.order_type.replace('_', ' ') }}</td>
              <td class="num py-2 text-right text-default">{{ order.quantity }}</td>
              <td class="num py-2 text-right text-default">{{ order.filled_quantity }}</td>
              <td class="num py-2 text-right text-default">{{ order.remaining_quantity }}</td>
              <td class="py-2 text-right"><PriceValue :value="order.limit_price" /></td>
              <td class="py-2 text-right"><PriceValue :value="order.average_fill_price" /></td>
              <td class="num py-2 text-right text-muted">
                {{ formatCurrency(order.fees, { currency: 'USD' }) }}
              </td>
              <td class="py-2 text-right">
                <NuxtLink :to="`/orders/${order.id}`"><OrderStatusBadge :status="order.status" /></NuxtLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState
        v-else
        title="No orders"
        message="Executed proposals and manual paper orders appear here."
        icon="i-lucide-clipboard-list"
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
