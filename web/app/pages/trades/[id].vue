<script setup lang="ts">
import { useTrade } from '~/composables/useTrades'
import { formatCurrency } from '~/utils/currency'
import { formatDateTime, formatDuration } from '~/utils/dates'
import { formatPercentage } from '~/utils/percentage'

const route = useRoute()
const tradeId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Trade ${tradeId.value}` })

const tradeQuery = useTrade(tradeId)
const trade = computed(() => tradeQuery.data.value ?? null)

const summary = computed(() => {
  const t = trade.value
  if (!t) return []
  return [
    { label: 'Symbol', value: t.symbol },
    { label: 'Side', value: t.side },
    { label: 'Quantity', value: String(t.quantity) },
    { label: 'Entry price', value: formatCurrency(t.entry_price, { currency: 'USD' }) },
    { label: 'Exit price', value: t.exit_price === null ? '—' : formatCurrency(t.exit_price, { currency: 'USD' }) },
    { label: 'Fees', value: formatCurrency(t.fees, { currency: 'USD' }) },
    { label: 'Opened', value: formatDateTime(t.opened_at) },
    { label: 'Closed', value: formatDateTime(t.closed_at) },
    { label: 'Duration', value: formatDuration(t.duration_seconds) },
  ]
})
</script>

<template>
  <div>
    <PageHeader
      :title="trade ? `${trade.symbol} trade` : `Trade ${tradeId}`"
      subtitle="Round-trip trade: entry, exit and realized P&L."
      eyebrow="Trade"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-arrow-left" to="/trades">
          All trades
        </UButton>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="tradeQuery.isLoading.value" @click="tradeQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="tradeQuery.isError.value"
      title="Trade unavailable"
      message="This trade could not be loaded. It may not exist, or the backend is unreachable."
      @retry="tradeQuery.refetch()"
    />
    <LoadingSkeleton v-else-if="tradeQuery.isLoading.value" :rows="6" />

    <template v-else-if="trade">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <StatusBadge :label="trade.status" :tone="trade.status === 'CLOSED' ? 'success' : 'warning'" dot />
        <StatusBadge :label="trade.side" :tone="trade.side === 'BUY' ? 'success' : 'danger'" />
      </div>

      <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Realized P&L" :value="trade.status === 'CLOSED' ? formatCurrency(trade.pnl, { currency: 'USD' }) : 'Open'" />
        <MetricCard label="Return" :value="trade.status === 'CLOSED' ? formatPercentage(trade.return_pct, { showSign: true }) : '—'" />
        <MetricCard label="Entry" :value="formatCurrency(trade.entry_price, { currency: 'USD' })" />
        <MetricCard label="Exit" :value="trade.exit_price === null ? '—' : formatCurrency(trade.exit_price, { currency: 'USD' })" />
      </section>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="rounded-lg border border-default bg-elevated/30 p-4 xl:col-span-2">
          <h2 class="text-sm font-semibold text-highlighted">Trade summary</h2>
          <dl class="mt-3 grid grid-cols-2 gap-y-3 text-xs">
            <template v-for="row in summary" :key="row.label">
              <dt class="text-muted">{{ row.label }}</dt>
              <dd class="text-right text-default">{{ row.value }}</dd>
            </template>
          </dl>
          <div class="mt-3 flex flex-wrap gap-3 text-xs">
            <NuxtLink v-if="trade.proposal_id" :to="`/agent/proposals/${trade.proposal_id}`" class="text-muted hover:text-highlighted">
              View originating proposal →
            </NuxtLink>
            <NuxtLink v-if="trade.order_ids.length" :to="`/orders/${trade.order_ids[0]}`" class="text-muted hover:text-highlighted">
              View linked order →
            </NuxtLink>
          </div>
        </div>

        <div class="rounded-lg border border-default bg-elevated/30 p-4">
          <h2 class="text-sm font-semibold text-highlighted">Audit chain</h2>
          <p class="mt-2 text-xs text-muted">
            Risk evaluations and executions are exposed through the originating proposal.
          </p>
          <NuxtLink
            v-if="trade.proposal_id"
            :to="`/agent/proposals/${trade.proposal_id}`"
            class="mt-2 inline-block text-xs text-muted hover:text-highlighted"
          >
            Open proposal pipeline →
          </NuxtLink>
          <p v-else class="mt-2 text-[11px] text-muted">
            This trade has no linked proposal. Execution-level detail is not exposed by the trades API.
          </p>
        </div>
      </section>
    </template>
  </div>
</template>
