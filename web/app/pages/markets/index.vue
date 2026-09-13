<script setup lang="ts">
import type { MarketRegime } from '~/types/market'
import { useMarkets } from '~/composables/useMarkets'
import { formatPrice } from '~/utils/currency'
import { formatDateTime } from '~/utils/dates'
import { regimeBreakdown, routeSymbol, topMovers } from '~/utils/market'

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

const overview = computed(() => marketsQuery.data.value ?? null)
const movers = computed(() => topMovers(items.value, 3))
const regimes = computed(() => regimeBreakdown(items.value))

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

const volumeFormat = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })

function rangeText(low: number | string | null, high: number | string | null): string {
  if (low === null && high === null) return '—'
  return `${formatPrice(low)} – ${formatPrice(high)}`
}

function ageText(seconds: number | null): string {
  if (seconds === null) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${Math.round(seconds / 3600)}h`
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

    <template v-else>
      <section v-if="overview" class="mb-3 flex flex-wrap items-center gap-2 text-xs">
        <StatusBadge :label="overview.is_open ? 'MARKET OPEN' : 'MARKET CLOSED'" :tone="overview.is_open ? 'success' : 'neutral'" dot />
        <StatusBadge :label="overview.session.replaceAll('_', ' ')" tone="neutral" />
        <StatusBadge :label="`provider · ${overview.provider}`" tone="neutral" />
        <StatusBadge :label="`regime · ${overview.regime.replaceAll('_', ' ')}`" :tone="regimeTone[overview.regime]" />
        <span class="text-muted">{{ overview.items.length }} symbols</span>
        <span class="text-muted">· as of {{ formatDateTime(overview.as_of) }}</span>
      </section>

      <section v-if="movers.gainers.length || movers.losers.length" class="mb-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div class="rounded-lg border border-default bg-elevated/30 p-3">
          <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">Top gainers</h2>
          <ul class="mt-2 space-y-1">
            <li v-for="item in movers.gainers" :key="item.symbol" class="flex items-center justify-between text-xs">
              <NuxtLink :to="`/markets/${routeSymbol(item.symbol)}`" class="hover:underline"><SymbolBadge :symbol="item.symbol" size="sm" /></NuxtLink>
              <span class="flex items-center gap-3">
                <PriceValue :value="item.price" />
                <PercentageValue :value="item.change_pct" show-sign colorize />
              </span>
            </li>
          </ul>
        </div>
        <div class="rounded-lg border border-default bg-elevated/30 p-3">
          <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">Top losers</h2>
          <ul class="mt-2 space-y-1">
            <li v-for="item in movers.losers" :key="item.symbol" class="flex items-center justify-between text-xs">
              <NuxtLink :to="`/markets/${routeSymbol(item.symbol)}`" class="hover:underline"><SymbolBadge :symbol="item.symbol" size="sm" /></NuxtLink>
              <span class="flex items-center gap-3">
                <PriceValue :value="item.price" />
                <PercentageValue :value="item.change_pct" show-sign colorize />
              </span>
            </li>
            <li v-if="!movers.losers.length" class="text-xs text-muted">No declining symbols.</li>
          </ul>
        </div>
      </section>

      <section v-if="regimes.length" class="mb-3 flex flex-wrap items-center gap-2">
        <span class="text-[11px] uppercase tracking-wide text-muted">Regime mix</span>
        <StatusBadge v-for="row in regimes" :key="row.regime" :label="`${row.regime.replaceAll('_', ' ')} ×${row.count}`" :tone="regimeTone[row.regime]" />
      </section>

      <div class="rounded-lg border border-default bg-elevated/30 p-4">
        <h2 class="mb-3 text-sm font-semibold text-highlighted">Watchlist</h2>
        <LoadingSkeleton v-if="marketsQuery.isLoading.value" :rows="5" />
        <div v-else-if="items.length" class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Symbol</th>
                <th class="pb-2 text-right font-medium">Last</th>
                <th class="pb-2 text-right font-medium">Bid</th>
                <th class="pb-2 text-right font-medium">Ask</th>
                <th class="pb-2 text-right font-medium">Change</th>
                <th class="pb-2 text-right font-medium">Change %</th>
                <th class="pb-2 text-right font-medium">Day range</th>
                <th class="pb-2 text-right font-medium">Prev close</th>
                <th class="pb-2 text-right font-medium">Volume</th>
                <th class="pb-2 font-medium">Signal</th>
                <th class="pb-2 font-medium">Regime</th>
                <th class="pb-2 text-right font-medium">Updated</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.symbol" class="border-t border-default hover:bg-elevated/40">
                <td class="py-2">
                  <NuxtLink :to="`/markets/${routeSymbol(item.symbol)}`" class="hover:underline">
                    <SymbolBadge :symbol="item.symbol" :name="item.name" size="sm" />
                  </NuxtLink>
                  <span class="ml-1 text-[10px] text-dimmed">{{ item.provider }}</span>
                </td>
                <td class="py-2 text-right"><PriceValue :value="item.price" /></td>
                <td class="py-2 text-right"><PriceValue :value="item.bid" /></td>
                <td class="py-2 text-right"><PriceValue :value="item.ask" /></td>
                <td class="py-2 text-right">
                  <PnLValue v-if="item.change !== null" :value="item.change" size="sm" show-arrow />
                  <span v-else class="text-muted">—</span>
                </td>
                <td class="py-2 text-right">
                  <PercentageValue v-if="item.change_pct !== null" :value="item.change_pct" show-sign colorize />
                  <span v-else class="text-muted">—</span>
                  <span v-if="item.change_window" class="ml-1 text-[10px] text-dimmed">{{ item.change_window }}</span>
                </td>
                <td class="num py-2 text-right text-muted">{{ rangeText(item.day_low, item.day_high) }}</td>
                <td class="py-2 text-right"><PriceValue :value="item.previous_close" /></td>
                <td class="num py-2 text-right text-muted">{{ item.volume === null ? '—' : volumeFormat.format(Number(item.volume)) }}</td>
                <td class="py-2">
                  <StatusBadge v-if="item.signal" :label="item.signal" :tone="directionTone[item.signal]" />
                  <span v-else class="text-muted">—</span>
                </td>
                <td class="py-2">
                  <StatusBadge v-if="item.market_regime" :label="item.market_regime.replace('_', ' ')" :tone="regimeTone[item.market_regime]" />
                  <span v-else class="text-muted">—</span>
                </td>
                <td class="py-2 text-right">
                  <StatusBadge v-if="item.market_closed" label="CLOSED" tone="neutral" />
                  <StatusBadge v-else-if="item.is_stale" label="STALE" tone="warning" />
                  <span v-else class="num text-muted">{{ ageText(item.age_seconds) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="No symbols" message="No watchlist symbols matched." icon="i-lucide-line-chart" />
      </div>
    </template>
  </div>
</template>
