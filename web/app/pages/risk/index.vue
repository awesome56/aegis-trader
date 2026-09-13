<script setup lang="ts">
import { useRiskEvents, useRiskLimits, useRiskStatus, useTradingControl, useTradingStatus } from '~/composables/useRisk'
import { formatCurrency } from '~/utils/currency'
import { formatDateTime } from '~/utils/dates'
import { formatPercentage } from '~/utils/percentage'
import { formatPnL } from '~/utils/pnl'

useHead({ title: 'Risk' })

const statusQuery = useRiskStatus()
const limitsQuery = useRiskLimits()
const eventsQuery = useRiskEvents()
const tradingQuery = useTradingStatus()
const controls = useTradingControl()

const status = computed(() => statusQuery.data.value ?? null)
const limits = computed(() => limitsQuery.data.value ?? [])
const events = computed(() => eventsQuery.data.value?.items ?? [])
const tradingState = computed(() => tradingQuery.data.value?.trading_state ?? 'TRADING_ENABLED')

const riskMetrics = computed(() => {
  const s = status.value
  if (!s) return []
  return [
    { key: 'exposure', label: 'Exposure', value: formatPercentage(s.exposure_pct), hint: `limit ${formatPercentage(s.max_exposure_pct)}`, bar: ratio(s.exposure_pct, s.max_exposure_pct) },
    { key: 'drawdown', label: 'Drawdown', value: formatPercentage(s.current_drawdown_pct), hint: `limit ${formatPercentage(s.max_drawdown_pct)}`, bar: ratio(s.current_drawdown_pct, s.max_drawdown_pct) },
    { key: 'daily_pnl', label: 'Daily P&L', value: formatPnL(s.daily_pnl, 'USD'), hint: `stop ${formatCurrency(s.daily_loss_limit, { currency: 'USD' })}`, bar: null },
    { key: 'positions', label: 'Open Positions', value: `${s.open_positions}`, hint: `of ${s.max_open_positions}`, bar: ratio(s.open_positions, s.max_open_positions) },
    { key: 'trades', label: 'Trades Today', value: `${s.trades_today}`, hint: `of ${s.max_trades_per_day}`, bar: ratio(s.trades_today, s.max_trades_per_day) },
    { key: 'buying_power', label: 'Buying Power', value: formatCurrency(s.buying_power, { currency: 'USD' }), hint: null, bar: null },
  ]
})

function ratio(current: number | string, limit: number | string): number {
  const denominator = Number(limit)
  if (!denominator) return 0
  return Math.min(100, (Number(current) / denominator) * 100)
}

const tone: Record<string, 'success' | 'warning' | 'danger'> = {
  SAFE: 'success',
  WARNING: 'warning',
  CRITICAL: 'danger',
}

type Action = 'pause' | 'resume' | 'enable' | 'disable' | 'emergency'

const dialog = reactive({ open: false, action: 'pause' as Action, loading: false })

const actionConfig: Record<Action, { title: string; description: string; tone: 'default' | 'danger'; confirmLabel: string; phrase?: string; consequences?: string[] }> = {
  pause: {
    title: 'Pause trading',
    description: 'New orders are blocked until trading is resumed.',
    tone: 'default',
    confirmLabel: 'Pause',
  },
  resume: {
    title: 'Resume trading',
    description: 'Allow new orders to be submitted again.',
    tone: 'default',
    confirmLabel: 'Resume',
  },
  enable: {
    title: 'Enable trading',
    description: 'Return the system to normal trading.',
    tone: 'default',
    confirmLabel: 'Enable',
  },
  disable: {
    title: 'Disable trading',
    description: 'Block all new trading until explicitly re-enabled.',
    tone: 'danger',
    confirmLabel: 'Disable',
    phrase: 'DISABLE',
    consequences: ['No new orders', 'Open positions are unaffected'],
  },
  emergency: {
    title: 'Emergency stop',
    description: 'Immediately halt all automated trading.',
    tone: 'danger',
    confirmLabel: 'Emergency stop',
    phrase: 'EMERGENCY STOP',
    consequences: ['All new trading halted', 'Requires explicit resume'],
  },
}

const activeConfig = computed(() => actionConfig[dialog.action])

function openDialog(action: Action): void {
  dialog.action = action
  dialog.open = true
}

async function runAction(): Promise<void> {
  dialog.loading = true
  try {
    if (dialog.action === 'pause') await controls.pause.mutateAsync('manual')
    else if (dialog.action === 'resume') await controls.resume.mutateAsync()
    else if (dialog.action === 'enable') await controls.enable.mutateAsync()
    else if (dialog.action === 'disable') await controls.disable.mutateAsync('manual')
    else await controls.emergencyStop.mutateAsync('manual emergency stop')
    dialog.open = false
  } finally {
    dialog.loading = false
  }
}
</script>

<template>
  <div>
    <PageHeader title="Risk" subtitle="Deterministic risk-control centre." eyebrow="Risk engine">
      <template #actions>
        <StatusBadge
          :label="tradingState.replace('TRADING_', '')"
          :tone="tradingState === 'EMERGENCY_STOP' ? 'danger' : tradingState === 'TRADING_ENABLED' ? 'success' : 'warning'"
          dot
        />
        <UButton
          color="neutral"
          variant="outline"
          size="sm"
          icon="i-lucide-refresh-cw"
          :loading="statusQuery.isLoading.value"
          @click="statusQuery.refetch(); limitsQuery.refetch(); eventsQuery.refetch()"
        >
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="statusQuery.isError.value"
      title="Risk status unavailable"
      message="The backend did not return a risk overview. Check the connection and retry."
      @retry="statusQuery.refetch()"
    />

    <template v-else>
      <section class="rounded-lg border border-default bg-elevated/30 p-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-highlighted">Overall risk</h2>
          <StatusBadge v-if="status" :label="status.level" :tone="tone[status.level]" />
        </div>
        <LoadingSkeleton v-if="statusQuery.isLoading.value" class="mt-4" :rows="3" />
        <div v-else-if="status" class="mt-3 grid grid-cols-2 gap-4 lg:grid-cols-3">
          <div v-for="metric in riskMetrics" :key="metric.key">
            <p class="text-[11px] font-medium uppercase tracking-wide text-muted">{{ metric.label }}</p>
            <p class="num mt-1 text-lg font-semibold text-highlighted">{{ metric.value }}</p>
            <p v-if="metric.hint" class="text-[11px] text-muted">{{ metric.hint }}</p>
            <div v-if="metric.bar !== null" class="mt-1 h-1.5 overflow-hidden rounded bg-elevated">
              <div class="h-full rounded bg-accented" :style="{ width: `${metric.bar}%` }" />
            </div>
          </div>
        </div>
      </section>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="rounded-lg border border-default bg-elevated/30 p-4 xl:col-span-2">
          <h2 class="text-sm font-semibold text-highlighted">Risk limits</h2>
          <LoadingSkeleton v-if="limitsQuery.isLoading.value" class="mt-4" :rows="4" />
          <div v-else-if="limits.length" class="mt-3 overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="text-muted">
                <tr>
                  <th class="pb-2 font-medium">Limit</th>
                  <th class="pb-2 text-right font-medium">Current</th>
                  <th class="pb-2 text-right font-medium">Limit</th>
                  <th class="pb-2 text-right font-medium">Used</th>
                  <th class="pb-2 text-right font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="limit in limits" :key="limit.key" class="border-t border-default">
                  <td class="py-2 text-default">{{ limit.label }}</td>
                  <td class="num py-2 text-right text-default">{{ limit.current }}</td>
                  <td class="num py-2 text-right text-muted">{{ limit.limit }}</td>
                  <td class="py-2 text-right">
                    <div class="flex items-center justify-end gap-2">
                      <div class="h-1.5 w-16 overflow-hidden rounded bg-elevated">
                        <div class="h-full rounded bg-accented" :style="{ width: `${Math.min(100, Number(limit.used_pct))}%` }" />
                      </div>
                      <span class="num w-12 text-right text-muted">{{ formatPercentage(limit.used_pct) }}</span>
                    </div>
                  </td>
                  <td class="py-2 text-right"><StatusBadge :label="limit.status" :tone="tone[limit.status]" /></td>
                </tr>
              </tbody>
            </table>
          </div>
          <EmptyState v-else title="No risk limits configured" icon="i-lucide-shield" />
        </div>

        <div class="rounded-lg border border-default bg-elevated/30 p-4">
          <h2 class="text-sm font-semibold text-highlighted">Trading controls</h2>
          <p class="mt-1 text-[11px] text-muted">Dangerous actions require confirmation.</p>
          <LoadingSkeleton v-if="tradingQuery.isLoading.value" class="mt-4" :rows="2" />
          <div v-else class="mt-3 grid grid-cols-2 gap-2">
            <UButton color="neutral" variant="outline" size="sm" :disabled="tradingState === 'TRADING_PAUSED'" @click="openDialog('pause')">
              Pause
            </UButton>
            <UButton color="neutral" variant="outline" size="sm" :disabled="tradingState === 'TRADING_ENABLED'" @click="openDialog('resume')">
              Resume
            </UButton>
            <UButton color="neutral" variant="outline" size="sm" @click="openDialog('enable')">
              Enable
            </UButton>
            <UButton color="warning" variant="outline" size="sm" @click="openDialog('disable')">
              Disable
            </UButton>
            <UButton class="col-span-2" color="error" variant="solid" size="sm" icon="i-lucide-octagon-x" @click="openDialog('emergency')">
              Emergency stop
            </UButton>
          </div>
          <p v-if="tradingQuery.data.value?.changed_at" class="mt-3 text-[11px] text-muted">
            Last change {{ formatDateTime(tradingQuery.data.value.changed_at) }}
            <span v-if="tradingQuery.data.value.actor"> by {{ tradingQuery.data.value.actor }}</span>
          </p>
        </div>
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <h2 class="text-sm font-semibold text-highlighted">Risk events</h2>
        <LoadingSkeleton v-if="eventsQuery.isLoading.value" class="mt-4" :rows="3" />
        <ul v-else-if="events.length" class="mt-3 space-y-2">
          <li v-for="event in events" :key="event.id" class="flex items-start justify-between gap-3 border-t border-default pt-2 first:border-t-0 first:pt-0">
            <div class="min-w-0">
              <p class="text-xs text-default">{{ event.message }}</p>
              <p class="mt-0.5 text-[11px] text-muted">{{ event.type }} · {{ formatDateTime(event.created_at) }}</p>
            </div>
            <StatusBadge :label="event.level" :tone="tone[event.level]" />
          </li>
        </ul>
        <EmptyState v-else title="No risk events" message="Risk engine activity will appear here." icon="i-lucide-shield-alert" />
      </section>
    </template>

    <ConfirmationDialog
      v-model:open="dialog.open"
      :title="activeConfig.title"
      :description="activeConfig.description"
      :consequences="activeConfig.consequences"
      :tone="activeConfig.tone"
      :confirm-label="activeConfig.confirmLabel"
      :confirm-phrase="activeConfig.phrase"
      :loading="dialog.loading"
      @confirm="runAction"
    />
  </div>
</template>
