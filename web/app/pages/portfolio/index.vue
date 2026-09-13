<script setup lang="ts">
import type { PortfolioRange } from '~/types/portfolio'
import { useAllocation, usePortfolio, usePortfolioHistory } from '~/composables/usePortfolio'
import { usePositions } from '~/composables/usePositions'
import { formatCurrency } from '~/utils/currency'
import { formatPercentage, formatSignedPercentage } from '~/utils/percentage'
import { formatPnL } from '~/utils/pnl'

useHead({ title: 'Portfolio' })

const summaryQuery = usePortfolio()
const allocationQuery = useAllocation()
const positionsQuery = usePositions()

const range = ref<PortfolioRange>('1M')
const historyQuery = usePortfolioHistory(range)

const RANGES: PortfolioRange[] = ['1D', '1W', '1M', '3M', '6M', 'YTD', '1Y', 'ALL']

const data = computed(() => summaryQuery.data.value ?? null)
const currency = computed(() => data.value?.currency ?? 'USD')

const metrics = computed(() => {
  const p = data.value
  if (!p) return []
  return [
    { label: 'Total Equity', value: formatCurrency(p.equity, { currency: p.currency }), delta: formatSignedPercentage(p.total_return_pct), tone: Number(p.total_return_pct) < 0 ? 'down' : 'up' },
    { label: 'Cash', value: formatCurrency(p.cash, { currency: p.currency }), delta: null, tone: 'flat' },
    { label: 'Invested', value: formatCurrency(p.invested, { currency: p.currency }), delta: null, tone: 'flat' },
    { label: 'Buying Power', value: formatCurrency(p.buying_power, { currency: p.currency }), delta: null, tone: 'flat' },
    { label: 'Daily P&L', value: formatPnL(p.daily_pnl, p.currency), delta: formatSignedPercentage(p.daily_return_pct), tone: Number(p.daily_pnl) < 0 ? 'down' : 'up' },
    { label: 'Total P&L', value: formatPnL(p.total_pnl, p.currency), delta: null, tone: 'flat' },
    { label: 'Unrealized P&L', value: formatPnL(p.unrealized_pnl, p.currency), delta: null, tone: 'flat' },
    { label: 'Exposure', value: formatPercentage(p.exposure_pct), delta: `${p.open_positions} positions`, tone: 'flat' },
  ] as { label: string; value: string; delta: string | null; tone: 'up' | 'down' | 'flat' }[]
})
</script>

<template>
  <div>
    <PageHeader title="Portfolio" subtitle="Holdings, allocation and performance analytics." eyebrow="Analytics">
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="summaryQuery.isLoading.value" @click="summaryQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="summaryQuery.isError.value"
      title="Portfolio unavailable"
      message="The backend did not return a portfolio summary. Check the connection and retry."
      @retry="summaryQuery.refetch()"
    />

    <template v-else>
      <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard
          v-for="metric in metrics"
          :key="metric.label"
          :label="metric.label"
          :value="metric.value"
          :delta="metric.delta"
          :delta-tone="metric.tone"
          :loading="summaryQuery.isLoading.value"
        />
      </section>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="rounded-lg border border-default bg-elevated/30 p-4 xl:col-span-2">
          <div class="mb-2 flex justify-end gap-1">
            <button
              v-for="option in RANGES"
              :key="option"
              type="button"
              class="rounded px-1.5 py-0.5 text-[11px] font-medium transition-colors"
              :class="range === option ? 'bg-elevated text-highlighted' : 'text-muted hover:text-default'"
              @click="range = option"
            >
              {{ option }}
            </button>
          </div>
          <EquityCurve
            :points="historyQuery.data.value?.points ?? []"
            :loading="historyQuery.isLoading.value"
            benchmark
          />
        </div>
        <div class="rounded-lg border border-default bg-elevated/30 p-4">
          <AllocationBars
            :breakdown="allocationQuery.data.value ?? null"
            :loading="allocationQuery.isLoading.value"
            :currency="currency"
          />
        </div>
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-highlighted">Positions</h2>
          <NuxtLink to="/positions" class="text-xs text-muted hover:text-highlighted">Open positions</NuxtLink>
        </div>
        <PositionsTable
          :positions="positionsQuery.data.value?.items ?? []"
          :loading="positionsQuery.isLoading.value"
          :currency="currency"
        />
      </section>
    </template>
  </div>
</template>
