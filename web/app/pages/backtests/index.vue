<script setup lang="ts">
import type { BacktestConfig, BacktestStatus } from '~/types/backtest'
import { useBacktests, useRunBacktest } from '~/composables/useBacktests'
import { useStrategies } from '~/composables/useStrategies'
import { formatPercentage } from '~/utils/percentage'

useHead({ title: 'Backtests' })

const backtestsQuery = useBacktests()
const strategiesQuery = useStrategies()
const runBacktest = useRunBacktest()
const router = useRouter()

const backtests = computed(() => backtestsQuery.data.value?.items ?? [])
const strategies = computed(() => strategiesQuery.data.value ?? [])

const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d', '1w']

const form = reactive({
  strategy_id: '',
  symbol: 'AAPL',
  timeframe: '1d',
  start_date: '2025-01-01',
  end_date: '2025-06-01',
  initial_capital: '100000',
  fees_pct: '0',
  slippage_pct: '0',
  benchmark_symbol: '',
})

watchEffect(() => {
  if (!form.strategy_id && strategies.value.length) {
    form.strategy_id = strategies.value[0]!.id
  }
})

const errorMessage = ref<string | null>(null)

async function submit(): Promise<void> {
  errorMessage.value = null
  if (!form.strategy_id) {
    errorMessage.value = 'Select a strategy.'
    return
  }
  if (!form.symbol.trim()) {
    errorMessage.value = 'Symbol is required.'
    return
  }
  try {
    const config: BacktestConfig = {
      strategy_id: form.strategy_id,
      symbols: [form.symbol.trim().toUpperCase()],
      timeframe: form.timeframe,
      start_date: form.start_date,
      end_date: form.end_date,
      initial_capital: form.initial_capital,
      fees_pct: form.fees_pct || undefined,
      slippage_pct: form.slippage_pct || undefined,
      benchmark_symbol: form.benchmark_symbol.trim().toUpperCase() || undefined,
    }
    const created = await runBacktest.mutateAsync(config)
    await router.push(`/backtests/${created.id}`)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Backtest failed to start.'
  }
}

const statusTone: Record<BacktestStatus, 'neutral' | 'info' | 'success' | 'danger' | 'warning'> = {
  PENDING: 'neutral',
  RUNNING: 'info',
  COMPLETED: 'success',
  FAILED: 'danger',
  CANCELLED: 'warning',
}
</script>

<template>
  <div>
    <PageHeader
      title="Backtests"
      subtitle="Deterministic historical simulation using the production strategies. Past performance does not guarantee future results."
      eyebrow="Research"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="backtestsQuery.isLoading.value" @click="backtestsQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <section class="rounded-lg border border-default bg-elevated/30 p-4">
      <h2 class="text-sm font-semibold text-highlighted">New backtest</h2>
      <p class="mt-1 text-[11px] text-muted">
        Simulation only — this never touches paper/live positions, orders or cash.
      </p>
      <div v-if="errorMessage" class="mt-2 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
        {{ errorMessage }}
      </div>
      <div class="mt-3 flex flex-wrap items-end gap-2">
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bt-strategy">Strategy</label>
          <select id="bt-strategy" v-model="form.strategy_id" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
            <option v-for="strategy in strategies" :key="strategy.id" :value="strategy.id">{{ strategy.name }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bt-symbol">Symbol</label>
          <UInput id="bt-symbol" v-model="form.symbol" placeholder="AAPL" class="w-24" />
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bt-tf">Timeframe</label>
          <select id="bt-tf" v-model="form.timeframe" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
            <option v-for="tf in TIMEFRAMES" :key="tf" :value="tf">{{ tf }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bt-start">Start</label>
          <input id="bt-start" v-model="form.start_date" type="date" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default" />
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bt-end">End</label>
          <input id="bt-end" v-model="form.end_date" type="date" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default" />
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bt-capital">Capital</label>
          <UInput id="bt-capital" v-model="form.initial_capital" class="w-28" />
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bt-fees">Fees %</label>
          <UInput id="bt-fees" v-model="form.fees_pct" class="w-20" />
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bt-slip">Slippage %</label>
          <UInput id="bt-slip" v-model="form.slippage_pct" class="w-20" />
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bt-bench">Benchmark</label>
          <UInput id="bt-bench" v-model="form.benchmark_symbol" placeholder="SPY" class="w-20" />
        </div>
        <UButton color="primary" size="sm" icon="i-lucide-play" :loading="runBacktest.isPending.value" @click="submit">
          Run backtest
        </UButton>
      </div>
    </section>

    <ErrorState
      v-if="backtestsQuery.isError.value"
      title="Backtests unavailable"
      message="The backtest API did not respond. Check the backend connection and retry."
      @retry="backtestsQuery.refetch()"
    />

    <div v-else class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
      <h2 class="text-sm font-semibold text-highlighted">Backtest history</h2>
      <LoadingSkeleton v-if="backtestsQuery.isLoading.value" class="mt-3" :rows="4" />
      <div v-else-if="backtests.length" class="mt-3 overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="text-muted">
            <tr>
              <th class="pb-2 font-medium">Name</th>
              <th class="pb-2 font-medium">Strategy</th>
              <th class="pb-2 font-medium">Symbol</th>
              <th class="pb-2 font-medium">TF</th>
              <th class="pb-2 font-medium">Range</th>
              <th class="pb-2 text-right font-medium">Return</th>
              <th class="pb-2 text-right font-medium">Max DD</th>
              <th class="pb-2 text-right font-medium">Trades</th>
              <th class="pb-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="backtest in backtests" :key="backtest.id" class="border-t border-default hover:bg-elevated/40">
              <td class="py-2">
                <NuxtLink :to="`/backtests/${backtest.id}`" class="text-default hover:underline">{{ backtest.name }}</NuxtLink>
              </td>
              <td class="py-2 text-muted">{{ backtest.strategy_name ?? '—' }}</td>
              <td class="py-2 text-muted">{{ backtest.symbols.join(', ') }}</td>
              <td class="num py-2 text-muted">{{ backtest.timeframe }}</td>
              <td class="py-2 text-muted">{{ backtest.start_date }} → {{ backtest.end_date }}</td>
              <td class="py-2 text-right">
                <PercentageValue v-if="backtest.total_return_pct !== null" :value="backtest.total_return_pct" show-sign colorize />
                <span v-else class="text-muted">—</span>
              </td>
              <td class="py-2 text-right">
                <span v-if="backtest.max_drawdown_pct !== null" class="num text-muted">{{ formatPercentage(backtest.max_drawdown_pct) }}</span>
                <span v-else class="text-muted">—</span>
              </td>
              <td class="num py-2 text-right text-muted">{{ backtest.num_trades ?? '—' }}</td>
              <td class="py-2"><StatusBadge :label="backtest.status" :tone="statusTone[backtest.status]" dot /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else title="No backtests yet" message="Configure a run above to create one." icon="i-lucide-flask-conical" />
    </div>
  </div>
</template>
