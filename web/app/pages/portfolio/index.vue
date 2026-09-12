<script setup lang="ts">
import { usePortfolio } from '~/composables/usePortfolio'
import { formatCurrency } from '~/utils/currency'
import { formatPercentage, formatSignedPercentage } from '~/utils/percentage'
import { formatPnL } from '~/utils/pnl'

useHead({ title: 'Portfolio' })

const { data, isLoading, isError, refetch } = usePortfolio()

const metrics = computed(() => {
  const p = data.value
  if (!p) return []
  return [
    { label: 'Total Equity', value: formatCurrency(p.equity), delta: formatSignedPercentage(p.total_return_pct) },
    { label: 'Cash', value: formatCurrency(p.cash) },
    { label: 'Invested', value: formatCurrency(p.invested) },
    { label: 'Buying Power', value: formatCurrency(p.buying_power) },
    { label: 'Daily P&L', value: formatPnL(p.daily_pnl, p.currency) },
    { label: 'Total P&L', value: formatPnL(p.total_pnl, p.currency) },
    { label: 'Unrealized P&L', value: formatPnL(p.unrealized_pnl, p.currency) },
    { label: 'Exposure', value: formatPercentage(p.exposure_pct) },
  ]
})
</script>

<template>
  <div>
    <PageHeader title="Portfolio" subtitle="Holdings, allocation and performance analytics." eyebrow="Analytics">
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="isLoading" @click="refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="isError"
      title="Portfolio unavailable"
      message="GET /portfolio is not implemented by the backend yet."
      @retry="refetch()"
    />

    <template v-else>
      <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard
          v-for="(metric, index) in metrics"
          :key="index"
          :label="metric.label"
          :value="metric.value"
          :delta="'delta' in metric ? metric.delta : null"
          :loading="isLoading"
        />
      </section>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="xl:col-span-2">
          <FeaturePlaceholder title="Equity curve" phase="Phase 3" icon="i-lucide-chart-line" description="Equity history with drawdown and benchmark." />
        </div>
        <FeaturePlaceholder title="Allocation" phase="Phase 3" icon="i-lucide-donut" description="Asset, sector and asset-class allocation." />
      </section>

      <div class="mt-4">
        <FeaturePlaceholder title="Positions" phase="Phase 3" icon="i-lucide-table" description="Full positions table with weights and live P&L." />
      </div>
    </template>
  </div>
</template>
