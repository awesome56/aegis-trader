<script setup lang="ts">
import { useTrades } from '~/composables/useTrades'
import { formatCurrency } from '~/utils/currency'
import { formatDateTime, formatDuration } from '~/utils/dates'

useHead({ title: 'Trades' })

const symbolFilter = ref('')
const page = ref(1)
const pageSize = 50

const params = computed(() => ({
  page: page.value,
  pageSize,
  symbol: symbolFilter.value.trim() || undefined,
}))

const tradesQuery = useTrades(params)
const items = computed(() => tradesQuery.data.value?.items ?? [])
const total = computed(() => tradesQuery.data.value?.total ?? 0)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

watch(symbolFilter, () => {
  page.value = 1
})
</script>

<template>
  <div>
    <PageHeader
      title="Trades"
      subtitle="Completed round-trip trades. Realized P&L is authoritative from the backend."
      eyebrow="Trading"
    >
      <template #actions>
        <UInput v-model="symbolFilter" placeholder="Filter symbol…" icon="i-lucide-search" class="w-40" />
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="tradesQuery.isLoading.value" @click="tradesQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="tradesQuery.isError.value"
      title="Trades unavailable"
      message="The trades API did not respond. Check the backend connection and retry."
      @retry="tradesQuery.refetch()"
    />

    <div v-else class="rounded-lg border border-default bg-elevated/30 p-4">
      <LoadingSkeleton v-if="tradesQuery.isLoading.value" :rows="6" />
      <div v-else-if="items.length" class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="text-muted">
            <tr>
              <th class="pb-2 font-medium">Opened</th>
              <th class="pb-2 font-medium">Symbol</th>
              <th class="pb-2 font-medium">Side</th>
              <th class="pb-2 text-right font-medium">Qty</th>
              <th class="pb-2 text-right font-medium">Entry</th>
              <th class="pb-2 text-right font-medium">Exit</th>
              <th class="pb-2 text-right font-medium">Fees</th>
              <th class="pb-2 text-right font-medium">Realized P&L</th>
              <th class="pb-2 text-right font-medium">Return</th>
              <th class="pb-2 text-right font-medium">Duration</th>
              <th class="pb-2 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="trade in items" :key="trade.id" class="border-t border-default hover:bg-elevated/40">
              <td class="py-2 text-muted">
                <NuxtLink :to="`/trades/${trade.id}`" class="hover:underline">
                  {{ formatDateTime(trade.opened_at) }}
                </NuxtLink>
              </td>
              <td class="py-2"><SymbolBadge :symbol="trade.symbol" size="sm" /></td>
              <td class="py-2"><StatusBadge :label="trade.side" :tone="trade.side === 'BUY' ? 'success' : 'danger'" /></td>
              <td class="num py-2 text-right text-default">{{ trade.quantity }}</td>
              <td class="py-2 text-right"><PriceValue :value="trade.entry_price" /></td>
              <td class="py-2 text-right">
                <PriceValue v-if="trade.status === 'CLOSED'" :value="trade.exit_price" />
                <span v-else class="text-muted">—</span>
              </td>
              <td class="num py-2 text-right text-muted">{{ formatCurrency(trade.fees, { currency: 'USD' }) }}</td>
              <td class="py-2 text-right">
                <PnLValue v-if="trade.status === 'CLOSED'" :value="trade.pnl" size="sm" />
                <span v-else class="text-muted">open</span>
              </td>
              <td class="py-2 text-right">
                <PercentageValue v-if="trade.status === 'CLOSED'" :value="trade.return_pct" show-sign colorize />
                <span v-else class="text-muted">—</span>
              </td>
              <td class="py-2 text-right text-muted">{{ formatDuration(trade.duration_seconds) }}</td>
              <td class="py-2 text-right">
                <StatusBadge :label="trade.status" :tone="trade.status === 'CLOSED' ? 'success' : 'warning'" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState
        v-else
        title="No trades"
        message="Completed round trips appear here once positions are closed."
        icon="i-lucide-arrow-left-right"
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
