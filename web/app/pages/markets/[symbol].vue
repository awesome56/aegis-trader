<script setup lang="ts">
import type { CandleTimeframe } from '~/types/market'
import { useMarketAsset, useMarketCandles } from '~/composables/useMarkets'
import { formatCurrency } from '~/utils/currency'
import { formatDateTime } from '~/utils/dates'
import { formatPercentage } from '~/utils/percentage'

const route = useRoute()
const symbol = computed(() => String(route.params.symbol ?? '').toUpperCase())
useHead({ title: () => symbol.value })

const assetQuery = useMarketAsset(symbol)
const timeframe = ref<CandleTimeframe>('1D')
const candlesQuery = useMarketCandles(symbol, timeframe)
const TIMEFRAMES: CandleTimeframe[] = ['1m', '5m', '15m', '1H', '4H', '1D', '1W']

const asset = computed(() => assetQuery.data.value ?? null)
const quote = computed(() => asset.value?.quote ?? null)

const metrics = computed(() => {
  const q = quote.value
  if (!q) return []
  return [
    { label: 'Last', value: formatCurrency(q.price, { currency: 'USD' }) },
    { label: 'Change', value: `${formatPercentage(q.change_pct, { showSign: true })}` },
    { label: 'Bid', value: formatCurrency(q.bid, { currency: 'USD' }) },
    { label: 'Ask', value: formatCurrency(q.ask, { currency: 'USD' }) },
    { label: 'Day High', value: formatCurrency(q.day_high, { currency: 'USD' }) },
    { label: 'Day Low', value: formatCurrency(q.day_low, { currency: 'USD' }) },
    { label: 'Volume', value: q.volume === null ? '—' : String(q.volume) },
    { label: 'Quote time', value: formatDateTime(q.quote_time) },
  ]
})
</script>

<template>
  <div>
    <PageHeader
      :title="symbol"
      :subtitle="asset?.asset.name ?? 'Asset detail — quote, candles and strategy signals.'"
      eyebrow="Asset"
    >
      <template #actions>
        <StatusBadge
          v-if="quote"
          :label="quote.is_stale ? 'STALE' : 'LIVE'"
          :tone="quote.is_stale ? 'warning' : 'success'"
          dot
        />
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-arrow-left" to="/markets">
          Markets
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="assetQuery.isError.value"
      title="Asset unavailable"
      message="This symbol could not be loaded from the market-data provider."
      @retry="assetQuery.refetch()"
    />

    <template v-else>
      <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard
          v-for="metric in metrics"
          :key="metric.label"
          :label="metric.label"
          :value="metric.value"
          :loading="assetQuery.isLoading.value"
        />
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <div class="mb-2 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-highlighted">Price</h2>
          <div class="flex gap-1">
            <button
              v-for="option in TIMEFRAMES"
              :key="option"
              type="button"
              class="rounded px-1.5 py-0.5 text-[11px] font-medium transition-colors"
              :class="timeframe === option ? 'bg-elevated text-highlighted' : 'text-muted hover:text-default'"
              @click="timeframe = option"
            >
              {{ option }}
            </button>
          </div>
        </div>
        <CandleChart :candles="candlesQuery.data.value?.candles ?? []" :loading="candlesQuery.isLoading.value" />
      </section>
    </template>
  </div>
</template>
