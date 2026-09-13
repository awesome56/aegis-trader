<script setup lang="ts">
import { usePosition } from '~/composables/usePositions'
import { formatCurrency } from '~/utils/currency'
import { formatDuration } from '~/utils/dates'
import { formatPercentage } from '~/utils/percentage'
import { formatPnL } from '~/utils/pnl'

const route = useRoute()
const positionId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Position ${positionId.value}` })

const { data, isLoading, isError, refetch } = usePosition(positionId)
const currency = 'USD'

const elapsed = computed(() => {
  const opened = data.value?.opened_at
  if (!opened) return null
  return formatDuration(Date.now() / 1000 - Date.parse(opened) / 1000)
})
</script>

<template>
  <div>
    <PageHeader
      :title="data ? `${data.symbol} position` : `Position ${positionId}`"
      subtitle="Trading workspace — position detail and audit chain."
      eyebrow="Position"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-arrow-left" to="/positions">
          All positions
        </UButton>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="isLoading" @click="refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="isError"
      title="Position unavailable"
      message="This position could not be loaded. It may have been closed or the backend is unreachable."
      @retry="refetch()"
    />

    <LoadingSkeleton v-else-if="isLoading" :rows="6" />

    <template v-else-if="data">
      <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Market Value" :value="formatCurrency(data.market_value, { currency })" />
        <MetricCard label="Unrealized P&L" :value="formatPnL(data.unrealized_pnl, currency)" />
        <MetricCard label="Return" :value="formatPercentage(data.return_pct)" />
        <MetricCard label="Weight" :value="formatPercentage(data.weight_pct)" />
      </section>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div class="rounded-lg border border-default bg-elevated/30 p-4">
          <h2 class="text-sm font-semibold text-highlighted">Position</h2>
          <dl class="mt-3 grid grid-cols-2 gap-y-3 text-xs">
            <dt class="text-muted">Symbol</dt>
            <dd class="text-right"><SymbolBadge :symbol="data.symbol" :name="data.asset_name" size="sm" /></dd>
            <dt class="text-muted">Side</dt>
            <dd class="text-right text-default">{{ data.side }}</dd>
            <dt class="text-muted">Quantity</dt>
            <dd class="num text-right text-default">{{ data.quantity }}</dd>
            <dt class="text-muted">Average entry</dt>
            <dd class="text-right"><PriceValue :value="data.average_entry_price" /></dd>
            <dt class="text-muted">Current price</dt>
            <dd class="text-right"><PriceValue :value="data.current_price" /></dd>
            <dt class="text-muted">Cost basis</dt>
            <dd class="text-right"><PriceValue :value="data.average_entry_price" /></dd>
            <dt class="text-muted">Realized P&L</dt>
            <dd class="text-right"><PnLValue :value="data.realized_pnl" :currency="currency" size="sm" /></dd>
            <dt class="text-muted">Held for</dt>
            <dd class="text-right text-default">{{ elapsed ?? '—' }}</dd>
          </dl>
        </div>

        <div class="rounded-lg border border-default bg-elevated/30 p-4">
          <h2 class="text-sm font-semibold text-highlighted">Orders</h2>
          <div v-if="data.orders.length" class="mt-3 overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="text-muted">
                <tr>
                  <th class="pb-2 font-medium">Side</th>
                  <th class="pb-2 text-right font-medium">Qty</th>
                  <th class="pb-2 text-right font-medium">Fill</th>
                  <th class="pb-2 text-right font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="order in data.orders" :key="order.id" class="border-t border-default">
                  <td class="py-2">
                    <StatusBadge :label="order.side" :tone="order.side === 'BUY' ? 'success' : 'danger'" />
                  </td>
                  <td class="num py-2 text-right text-default">{{ order.quantity }}</td>
                  <td class="py-2 text-right"><PriceValue :value="order.average_fill_price" /></td>
                  <td class="py-2 text-right"><StatusBadge :label="order.status" tone="neutral" /></td>
                </tr>
              </tbody>
            </table>
          </div>
          <EmptyState
            v-else
            class="mt-3"
            title="No linked orders"
            message="Order-level detail is not exposed for this position yet."
            icon="i-lucide-receipt"
          />
        </div>
      </section>
    </template>
  </div>
</template>
