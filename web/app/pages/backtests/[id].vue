<script setup lang="ts">
import { useBacktest, useBacktestResult, useCancelBacktest } from '~/composables/useBacktests'
import { formatCurrency } from '~/utils/currency'
import { formatDateTime, formatDuration } from '~/utils/dates'
import { formatPercentage } from '~/utils/percentage'

const route = useRoute()
const backtestId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Backtest ${backtestId.value}` })

const backtestQuery = useBacktest(backtestId)
const backtest = computed(() => backtestQuery.data.value ?? null)
const isFinished = computed(() => backtest.value?.status === 'COMPLETED')

const resultQuery = useBacktestResult(computed(() => (isFinished.value ? backtestId.value : '')))
const result = computed(() => resultQuery.data.value ?? null)
const cancelBacktest = useCancelBacktest()

const equityPath = computed(() => {
  const points = result.value?.equity_curve ?? []
  if (points.length < 2) return ''
  const values = points.map((point) => Number(point.equity))
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 100
      const y = 34 - ((value - min) / span) * 30 - 2
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
})

const metrics = computed(() => {
  const m = result.value?.metrics
  if (!m) return []
  return [
    { label: 'Initial capital', value: formatCurrency(m.initial_capital, { currency: 'USD' }) },
    { label: 'Final capital', value: formatCurrency(m.final_capital, { currency: 'USD' }) },
    { label: 'Net profit', value: formatCurrency(m.net_profit, { currency: 'USD' }) },
    { label: 'Total return', value: formatPercentage(m.total_return_pct, { showSign: true }) },
    { label: 'Benchmark return', value: m.benchmark_return_pct === null ? '—' : formatPercentage(m.benchmark_return_pct, { showSign: true }) },
    { label: 'Max drawdown', value: formatPercentage(m.max_drawdown_pct) },
    { label: 'Sharpe', value: m.sharpe_ratio === null ? '—' : String(m.sharpe_ratio) },
    { label: 'Sortino', value: m.sortino_ratio === null ? '—' : String(m.sortino_ratio) },
    { label: 'Trades', value: `${m.num_trades}` },
    { label: 'Win rate', value: `${formatPercentage(m.win_rate)} (${m.wins}W / ${m.losses}L)` },
    { label: 'Profit factor', value: m.profit_factor === null ? '—' : String(m.profit_factor) },
    { label: 'Expectancy', value: formatCurrency(m.expectancy, { currency: 'USD' }) },
    { label: 'Fees', value: formatCurrency(m.total_fees, { currency: 'USD' }) },
    { label: 'Slippage', value: formatCurrency(m.total_slippage, { currency: 'USD' }) },
    { label: 'Exposure', value: formatPercentage(m.exposure_pct) },
    { label: 'Avg holding', value: formatDuration(Number(m.average_holding_seconds)) },
  ]
})
</script>

<template>
  <div>
    <PageHeader
      :title="backtest ? backtest.name : `Backtest ${backtestId}`"
      subtitle="Deterministic historical simulation. Past performance does not guarantee future results."
      eyebrow="Research"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-arrow-left" to="/backtests">
          All backtests
        </UButton>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="backtestQuery.isLoading.value" @click="backtestQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="backtestQuery.isError.value"
      title="Backtest unavailable"
      message="This backtest could not be loaded. It may not exist, or the backend is unreachable."
      @retry="backtestQuery.refetch()"
    />
    <LoadingSkeleton v-else-if="backtestQuery.isLoading.value" :rows="6" />

    <template v-else-if="backtest">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <StatusBadge :label="backtest.status" :tone="backtest.status === 'COMPLETED' ? 'success' : backtest.status === 'FAILED' ? 'danger' : backtest.status === 'RUNNING' ? 'info' : 'neutral'" dot />
        <StatusBadge :label="backtest.timeframe" tone="neutral" />
        <StatusBadge :label="backtest.symbols.join(', ')" tone="neutral" />
        <UButton
          v-if="backtest.status === 'PENDING'"
          color="warning"
          variant="outline"
          size="xs"
          :loading="cancelBacktest.isPending.value"
          @click="cancelBacktest.mutate(backtest.id)"
        >
          Cancel
        </UButton>
        <NuxtLink v-if="backtest.strategy_id" :to="`/strategies/${backtest.strategy_id}`" class="text-xs text-muted hover:text-highlighted">
          Strategy →
        </NuxtLink>
      </div>

      <p v-if="backtest.error" class="mb-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
        {{ backtest.error }}
      </p>

      <div v-if="backtest.status === 'PENDING' || backtest.status === 'RUNNING'" class="rounded-lg border border-default bg-elevated/30 p-4 text-xs text-muted">
        Backtest is {{ backtest.status.toLowerCase() }}. This page refreshes automatically while it runs.
      </div>

      <template v-else-if="isFinished">
        <LoadingSkeleton v-if="resultQuery.isLoading.value" :rows="6" />
        <ErrorState
          v-else-if="resultQuery.isError.value"
          title="Result unavailable"
          message="The result could not be loaded."
          @retry="resultQuery.refetch()"
        />
        <template v-else-if="result">
          <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MetricCard label="Total return" :value="formatPercentage(result.metrics.total_return_pct, { showSign: true })" />
            <MetricCard label="Final capital" :value="formatCurrency(result.metrics.final_capital, { currency: 'USD' })" />
            <MetricCard label="Max drawdown" :value="formatPercentage(result.metrics.max_drawdown_pct)" />
            <MetricCard label="Win rate" :value="formatPercentage(result.metrics.win_rate)" :hint="`${result.metrics.num_trades} trades`" />
          </section>

          <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
            <h2 class="text-sm font-semibold text-highlighted">Equity curve</h2>
            <svg
              v-if="equityPath"
              viewBox="0 0 100 34"
              preserveAspectRatio="none"
              class="mt-3 h-44 w-full text-accented"
              role="img"
              aria-label="Equity curve"
            >
              <path :d="equityPath" fill="none" stroke="currentColor" stroke-width="0.6" />
            </svg>
            <p v-else class="mt-2 text-xs text-muted">No equity points.</p>
          </section>

          <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
            <h2 class="text-sm font-semibold text-highlighted">Metrics</h2>
            <dl class="mt-3 grid grid-cols-2 gap-y-3 text-xs lg:grid-cols-4">
              <template v-for="row in metrics" :key="row.label">
                <dt class="text-muted">{{ row.label }}</dt>
                <dd class="text-right text-default">{{ row.value }}</dd>
              </template>
            </dl>
            <p class="mt-3 text-[11px] text-muted">
              Engine {{ result.engine_version }} · executed at next-candle open ·
              Sharpe/Sortino use a zero risk-free rate.
            </p>
          </section>

          <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
            <h2 class="text-sm font-semibold text-highlighted">Trades ({{ result.trades.length }})</h2>
            <div v-if="result.trades.length" class="mt-3 overflow-x-auto">
              <table class="w-full text-left text-xs">
                <thead class="text-muted">
                  <tr>
                    <th class="pb-2 font-medium">Symbol</th>
                    <th class="pb-2 font-medium">Side</th>
                    <th class="pb-2 text-right font-medium">Qty</th>
                    <th class="pb-2 font-medium">Entry</th>
                    <th class="pb-2 font-medium">Exit</th>
                    <th class="pb-2 text-right font-medium">Entry px</th>
                    <th class="pb-2 text-right font-medium">Exit px</th>
                    <th class="pb-2 text-right font-medium">Net P&L</th>
                    <th class="pb-2 text-right font-medium">Return</th>
                    <th class="pb-2 text-right font-medium">Exit reason</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(trade, index) in result.trades" :key="index" class="border-t border-default">
                    <td class="py-2"><SymbolBadge :symbol="trade.symbol" size="sm" /></td>
                    <td class="py-2"><StatusBadge :label="trade.side" tone="success" /></td>
                    <td class="num py-2 text-right text-default">{{ trade.quantity }}</td>
                    <td class="py-2 text-muted">{{ formatDateTime(trade.entry_time) }}</td>
                    <td class="py-2 text-muted">{{ formatDateTime(trade.exit_time) }}</td>
                    <td class="py-2 text-right"><PriceValue :value="trade.entry_price" /></td>
                    <td class="py-2 text-right"><PriceValue :value="trade.exit_price" /></td>
                    <td class="py-2 text-right"><PnLValue :value="trade.net_pnl" size="sm" /></td>
                    <td class="py-2 text-right"><PercentageValue :value="trade.return_pct" show-sign colorize /></td>
                    <td class="py-2 text-right text-muted">{{ trade.exit_reason }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <EmptyState v-else title="No trades" message="This configuration produced no trades." icon="i-lucide-list" />
          </section>
        </template>
      </template>
    </template>
  </div>
</template>
