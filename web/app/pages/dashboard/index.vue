<script setup lang="ts">
import type { SignalDirection } from '~/types/market'
import { useDashboard } from '~/composables/useDashboard'
import { useSystemStatus } from '~/composables/useSystemStatus'
import { formatCurrency } from '~/utils/currency'
import { formatPercentage, formatSignedPercentage } from '~/utils/percentage'
import { formatPnL } from '~/utils/pnl'
import { formatDateTime } from '~/utils/dates'

useHead({ title: 'Dashboard' })

const { data, isLoading, isError, refetch } = useDashboard()
const { statusQuery } = useSystemStatus()

const portfolio = computed(() => data.value?.summary.portfolio ?? null)
const risk = computed(() => data.value?.summary.risk ?? null)
const agent = computed(() => data.value?.summary.agent ?? null)
const positions = computed(() => data.value?.top_positions ?? [])
const trades = computed(() => data.value?.recent_trades ?? [])
const signals = computed(() => data.value?.strategy_signals ?? [])
const equityPoints = computed(() => data.value?.equity_history ?? [])

const metrics = computed(() => {
  const p = portfolio.value
  return [
    {
      key: 'equity',
      label: 'Portfolio Value',
      value: p ? formatCurrency(p.equity, { currency: p.currency }) : null,
      delta: p ? formatSignedPercentage(p.daily_return_pct) : null,
      deltaTone: Number(p?.daily_return_pct ?? 0) < 0 ? ('down' as const) : ('up' as const),
      hint: p ? `${formatCurrency(p.cash, { currency: p.currency })} cash` : null,
    },
    {
      key: 'pnl',
      label: "Today's P&L",
      value: p ? formatPnL(p.daily_pnl, p.currency) : null,
      delta: p ? formatSignedPercentage(p.daily_return_pct) : null,
      deltaTone: Number(p?.daily_pnl ?? 0) < 0 ? ('down' as const) : ('up' as const),
      hint: p ? `${formatPnL(p.total_pnl, p.currency)} total` : null,
    },
    {
      key: 'buying_power',
      label: 'Buying Power',
      value: p ? formatCurrency(p.buying_power, { currency: p.currency }) : null,
      delta: null,
      deltaTone: 'flat' as const,
      hint: null,
    },
    {
      key: 'exposure',
      label: 'Portfolio Exposure',
      value: p ? formatPercentage(p.exposure_pct) : null,
      delta: risk.value
        ? `${risk.value.open_positions}/${risk.value.max_open_positions} positions`
        : null,
      deltaTone: 'flat' as const,
      hint: risk.value ? `drawdown ${formatPercentage(risk.value.current_drawdown_pct)}` : null,
    },
  ]
})

const sparkPath = computed(() => {
  const points = equityPoints.value
    .map((point) => Number(point.equity))
    .filter((value) => Number.isFinite(value))
  if (points.length < 2) return ''
  const min = Math.min(...points)
  const max = Math.max(...points)
  const span = max - min || 1
  return points
    .map((value, index) => {
      const x = (index / (points.length - 1)) * 100
      const y = 30 - ((value - min) / span) * 28 - 1
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
})

const equityChange = computed(() => {
  const points = equityPoints.value
  if (points.length < 2) return null
  const firstPoint = points[0]
  const lastPoint = points[points.length - 1]
  if (!firstPoint || !lastPoint) return null
  const first = Number(firstPoint.equity)
  const last = Number(lastPoint.equity)
  if (!first) return null
  return ((last - first) / first) * 100
})

const killSwitchState = computed(() => statusQuery.data.value?.kill_switch_state ?? '—')

const directionTone: Record<SignalDirection, 'success' | 'danger' | 'neutral'> = {
  LONG: 'success',
  SHORT: 'danger',
  NEUTRAL: 'neutral',
}
</script>

<template>
  <div>
    <PageHeader
      title="Dashboard"
      subtitle="Real-time command centre — portfolio, risk and agent overview."
      eyebrow="Command centre"
    >
      <template #actions>
        <StatusBadge :label="killSwitchState.replace('TRADING_', '')" tone="neutral" dot />
        <UButton
          color="neutral"
          variant="outline"
          size="sm"
          icon="i-lucide-refresh-cw"
          :loading="isLoading"
          @click="refetch()"
        >
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="isError"
      title="Dashboard unavailable"
      message="The dashboard endpoints are unreachable. Check the backend connection or enable the mock API."
      @retry="refetch()"
    />

    <template v-else>
      <section aria-label="Key metrics" class="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <MetricCard
          v-for="metric in metrics"
          :key="metric.key"
          :label="metric.label"
          :value="metric.value"
          :delta="metric.delta"
          :delta-tone="metric.deltaTone"
          :hint="metric.hint"
          :loading="isLoading"
        />
      </section>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="rounded-lg border border-default bg-elevated/30 p-4 xl:col-span-2">
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-semibold text-highlighted">Portfolio performance</h2>
            <span v-if="equityChange !== null" class="num text-xs font-medium text-muted">
              1M
              <span :class="equityChange < 0 ? 'text-down' : 'text-up'">
                {{ formatSignedPercentage(equityChange) }}
              </span>
            </span>
          </div>
          <LoadingSkeleton v-if="isLoading" class="mt-4" :rows="4" height="h-10" />
          <div v-else-if="sparkPath" class="mt-4">
            <svg
              viewBox="0 0 100 30"
              preserveAspectRatio="none"
              class="h-32 w-full"
              role="img"
              aria-label="Equity curve"
            >
              <path :d="sparkPath" fill="none" stroke="currentColor" stroke-width="0.6" class="text-accented" />
            </svg>
            <div class="mt-1 flex justify-between text-[11px] text-muted">
              <span>{{ formatCurrency(equityPoints[0]?.equity, { currency: portfolio?.currency }) }}</span>
              <span>{{ formatCurrency(equityPoints[equityPoints.length - 1]?.equity, { currency: portfolio?.currency }) }}</span>
            </div>
          </div>
          <EmptyState
            v-else
            class="mt-4"
            title="No equity history yet"
            message="Snapshots accumulate every few minutes while the worker runs."
            icon="i-lucide-chart-area"
          />
        </div>

        <div class="rounded-lg border border-default bg-elevated/30 p-4">
          <h2 class="text-sm font-semibold text-highlighted">Risk & allocation</h2>
          <div v-if="isLoading" class="mt-4">
            <LoadingSkeleton :rows="4" />
          </div>
          <dl v-else-if="risk" class="mt-3 space-y-3">
            <div class="flex items-center justify-between">
              <dt class="text-xs text-muted">Risk level</dt>
              <dd>
                <StatusBadge
                  :label="risk.level"
                  :tone="risk.level === 'CRITICAL' ? 'danger' : risk.level === 'WARNING' ? 'warning' : 'success'"
                />
              </dd>
            </div>
            <div class="space-y-1">
              <div class="flex justify-between text-xs">
                <span class="text-muted">Exposure</span>
                <span class="num text-default">
                  {{ formatPercentage(risk.exposure_pct) }} / {{ formatPercentage(risk.max_exposure_pct) }}
                </span>
              </div>
              <div class="h-1.5 overflow-hidden rounded bg-elevated">
                <div
                  class="h-full rounded bg-accented"
                  :style="{
                    width: `${Math.min(100, (Number(risk.exposure_pct) / (Number(risk.max_exposure_pct) || 100)) * 100)}%`,
                  }"
                />
              </div>
            </div>
            <div class="space-y-1">
              <div class="flex justify-between text-xs">
                <span class="text-muted">Drawdown</span>
                <span class="num text-default">
                  {{ formatPercentage(risk.current_drawdown_pct) }} / {{ formatPercentage(risk.max_drawdown_pct) }}
                </span>
              </div>
              <div class="h-1.5 overflow-hidden rounded bg-elevated">
                <div
                  class="h-full rounded bg-accented"
                  :style="{
                    width: `${Math.min(100, (Number(risk.current_drawdown_pct) / (Number(risk.max_drawdown_pct) || 100)) * 100)}%`,
                  }"
                />
              </div>
            </div>
            <div class="flex items-center justify-between text-xs">
              <dt class="text-muted">Trades today</dt>
              <dd class="num text-default">{{ risk.trades_today }} / {{ risk.max_trades_per_day }}</dd>
            </div>
          </dl>
          <EmptyState v-else title="Risk unavailable" icon="i-lucide-shield-alert" />
        </div>
      </section>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="rounded-lg border border-default bg-elevated/30 p-4 xl:col-span-2">
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-semibold text-highlighted">Open positions</h2>
            <NuxtLink to="/positions" class="text-xs text-muted hover:text-highlighted">View all</NuxtLink>
          </div>
          <LoadingSkeleton v-if="isLoading" class="mt-4" :rows="4" />
          <div v-else-if="positions.length" class="mt-3 overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="text-muted">
                <tr>
                  <th class="pb-2 font-medium">Symbol</th>
                  <th class="pb-2 text-right font-medium">Qty</th>
                  <th class="pb-2 text-right font-medium">Avg entry</th>
                  <th class="pb-2 text-right font-medium">Price</th>
                  <th class="pb-2 text-right font-medium">Value</th>
                  <th class="pb-2 text-right font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="position in positions" :key="position.id" class="border-t border-default">
                  <td class="py-2"><SymbolBadge :symbol="position.symbol" size="sm" /></td>
                  <td class="num py-2 text-right text-default">{{ position.quantity }}</td>
                  <td class="py-2 text-right"><PriceValue :value="position.average_entry_price" /></td>
                  <td class="py-2 text-right"><PriceValue :value="position.current_price" /></td>
                  <td class="num py-2 text-right text-default">
                    {{ formatCurrency(position.market_value, { currency: portfolio?.currency }) }}
                  </td>
                  <td class="py-2 text-right">
                    <PnLValue :value="position.unrealized_pnl" :currency="portfolio?.currency" size="sm" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <EmptyState
            v-else
            class="mt-3"
            title="No open positions"
            message="Positions appear here once an approved proposal is executed."
            icon="i-lucide-briefcase"
          />
        </div>

        <div class="rounded-lg border border-default bg-elevated/30 p-4">
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-semibold text-highlighted">Strategy signals</h2>
            <span class="text-[11px] text-muted">
              {{ agent?.enabled ? 'Agent online' : 'Agent disabled' }}
            </span>
          </div>
          <LoadingSkeleton v-if="isLoading" class="mt-4" :rows="4" />
          <ul v-else-if="signals.length" class="mt-3 space-y-2">
            <li
              v-for="signal in signals"
              :key="signal.id"
              class="flex items-center justify-between gap-2 border-t border-default pt-2 first:border-t-0 first:pt-0"
            >
              <div class="min-w-0">
                <SymbolBadge :symbol="signal.symbol" :name="signal.strategy_name" size="sm" />
                <p class="mt-0.5 text-[11px] text-muted">
                  {{ signal.timeframe }} · {{ formatDateTime(signal.signal_time) }}
                </p>
              </div>
              <StatusBadge :label="signal.direction" :tone="directionTone[signal.direction]" />
            </li>
          </ul>
          <EmptyState v-else title="No recent signals" icon="i-lucide-workflow" />
        </div>
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-highlighted">Recent trades</h2>
          <NuxtLink to="/trades" class="text-xs text-muted hover:text-highlighted">View all</NuxtLink>
        </div>
        <LoadingSkeleton v-if="isLoading" class="mt-4" :rows="3" />
        <div v-else-if="trades.length" class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Symbol</th>
                <th class="pb-2 font-medium">Side</th>
                <th class="pb-2 text-right font-medium">Qty</th>
                <th class="pb-2 text-right font-medium">Entry</th>
                <th class="pb-2 text-right font-medium">Exit</th>
                <th class="pb-2 text-right font-medium">P&L</th>
                <th class="pb-2 text-right font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="trade in trades" :key="trade.id" class="border-t border-default">
                <td class="py-2"><SymbolBadge :symbol="trade.symbol" size="sm" /></td>
                <td class="py-2">
                  <StatusBadge :label="trade.side" :tone="trade.side === 'BUY' ? 'success' : 'danger'" />
                </td>
                <td class="num py-2 text-right text-default">{{ trade.quantity }}</td>
                <td class="py-2 text-right"><PriceValue :value="trade.entry_price" /></td>
                <td class="py-2 text-right"><PriceValue :value="trade.exit_price" /></td>
                <td class="py-2 text-right">
                  <PnLValue :value="trade.pnl" :currency="portfolio?.currency" size="sm" />
                </td>
                <td class="py-2 text-right">
                  <StatusBadge :label="trade.status" :tone="trade.status === 'CLOSED' ? 'success' : 'warning'" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState
          v-else
          title="No trades yet"
          message="Completed round trips will appear here."
          icon="i-lucide-history"
        />
      </section>
    </template>
  </div>
</template>
