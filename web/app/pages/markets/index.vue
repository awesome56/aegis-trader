<script setup lang="ts">
import type { MarketRegime } from '~/types/market'
import { useMarkets } from '~/composables/useMarkets'

useHead({ title: 'Markets' })

const marketsQuery = useMarkets()
const search = ref('')

const items = computed(() => {
  const rows = marketsQuery.data.value?.items ?? []
  const term = search.value.trim().toUpperCase()
  if (!term) return rows
  return rows.filter(
    (row) => row.symbol.includes(term) || (row.name ?? '').toUpperCase().includes(term),
  )
})

const directionTone: Record<string, 'success' | 'danger' | 'neutral'> = {
  LONG: 'success',
  SHORT: 'danger',
  NEUTRAL: 'neutral',
}

const regimeTone: Record<MarketRegime, 'success' | 'danger' | 'warning' | 'neutral'> = {
  BULLISH: 'success',
  BEARISH: 'danger',
  SIDEWAYS: 'neutral',
  HIGH_VOLATILITY: 'warning',
  LOW_VOLATILITY: 'neutral',
  UNKNOWN: 'neutral',
}
</script>

<template>
  <div>
    <PageHeader title="Markets" subtitle="Watchlist, quotes, market regime and strategy signals." eyebrow="Market data">
      <template #actions>
        <UInput v-model="search" size="sm" placeholder="Filter symbol…" icon="i-lucide-search" class="w-48" />
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="marketsQuery.isLoading.value" @click="marketsQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="marketsQuery.isError.value"
      title="Markets unavailable"
      message="The backend did not return a market overview. Check the connection and retry."
      @retry="marketsQuery.refetch()"
    />

    <div v-else class="rounded-lg border border-default bg-elevated/30 p-4">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-highlighted">Watchlist</h2>
        <span v-if="marketsQuery.data.value" class="text-[11px] text-muted">
          {{ marketsQuery.data.value.regime }}
          · {{ marketsQuery.data.value.items.length }} symbols
        </span>
      </div>
      <LoadingSkeleton v-if="marketsQuery.isLoading.value" :rows="5" />
      <div v-else-if="items.length" class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="text-muted">
            <tr>
              <th class="pb-2 font-medium">Symbol</th>
              <th class="pb-2 text-right font-medium">Price</th>
              <th class="pb-2 text-right font-medium">Change</th>
              <th class="pb-2 text-right font-medium">Volume</th>
              <th class="pb-2 font-medium">Signal</th>
              <th class="pb-2 font-medium">Regime</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.symbol" class="border-t border-default hover:bg-elevated/40">
              <td class="py-2">
                <NuxtLink :to="`/markets/${item.symbol}`" class="hover:underline">
                  <SymbolBadge :symbol="item.symbol" :name="item.name" size="sm" />
                </NuxtLink>
              </td>
              <td class="py-2 text-right"><PriceValue :value="item.price" /></td>
              <td class="py-2 text-right">
                <PercentageValue v-if="item.change_pct !== null" :value="item.change_pct" show-sign colorize />
                <span v-else class="text-muted">—</span>
              </td>
              <td class="num py-2 text-right text-muted">{{ item.volume ?? '—' }}</td>
              <td class="py-2">
                <StatusBadge v-if="item.signal" :label="item.signal" :tone="directionTone[item.signal]" />
                <span v-else class="text-muted">—</span>
              </td>
              <td class="py-2">
                <StatusBadge v-if="item.market_regime" :label="item.market_regime.replace('_', ' ')" :tone="regimeTone[item.market_regime]" />
                <span v-else class="text-muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else title="No symbols" message="No watchlist symbols matched." icon="i-lucide-line-chart" />
    </div>
  </div>
</template>
