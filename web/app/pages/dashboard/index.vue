<script setup lang="ts">
import { useDashboard } from '~/composables/useDashboard'
import { useSystemStatus } from '~/composables/useSystemStatus'
import { formatCurrency } from '~/utils/currency'
import { formatPercentage, formatSignedPercentage } from '~/utils/percentage'
import { formatPnL } from '~/utils/pnl'

useHead({ title: 'Dashboard' })

const { data, isLoading, isError, refetch } = useDashboard()
const { statusQuery } = useSystemStatus()

const portfolio = computed(() => data.value?.summary.portfolio ?? null)
const risk = computed(() => data.value?.summary.risk ?? null)
const agent = computed(() => data.value?.summary.agent ?? null)

const metrics = computed(() => {
  const p = portfolio.value
  return [
    {
      key: 'equity',
      label: 'Portfolio Value',
      value: p ? formatCurrency(p.equity) : null,
      delta: p ? formatSignedPercentage(p.daily_return_pct) : null,
      deltaTone: 'up' as const,
    },
    {
      key: 'pnl',
      label: "Today's P&L",
      value: p ? formatPnL(p.daily_pnl, p.currency) : null,
      delta: p ? formatSignedPercentage(p.daily_return_pct) : null,
      deltaTone: 'up' as const,
    },
    {
      key: 'buying_power',
      label: 'Buying Power',
      value: p ? formatCurrency(p.buying_power) : null,
      delta: null,
      deltaTone: 'flat' as const,
    },
    {
      key: 'exposure',
      label: 'Portfolio Exposure',
      value: p ? formatPercentage(p.exposure_pct) : null,
      delta: risk.value ? `${risk.value.open_positions}/${risk.value.max_open_positions} positions` : null,
      deltaTone: 'flat' as const,
    },
  ]
})

const killSwitchState = computed(() => statusQuery.data.value?.kill_switch_state ?? '—')
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
      message="The dashboard endpoint is not available yet, or the backend is unreachable. Enable NUXT_PUBLIC_USE_MOCK_API for local development."
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
          :loading="isLoading"
        />
      </section>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="xl:col-span-2">
          <FeaturePlaceholder
            title="Portfolio performance"
            phase="Phase 2"
            icon="i-lucide-chart-area"
            description="Equity curve with 1D–ALL ranges, benchmark overlay and drawdown shading."
          />
        </div>
        <FeaturePlaceholder
          title="Risk & allocation"
          phase="Phase 2"
          icon="i-lucide-shield-alert"
          description="Exposure, drawdown and allocation breakdown."
        />
      </section>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="xl:col-span-2">
          <FeaturePlaceholder
            title="Open positions"
            phase="Phase 3"
            icon="i-lucide-table"
            description="Compact positions table with live P&L."
          />
        </div>
        <div class="space-y-4">
          <FeaturePlaceholder
            title="Agent activity"
            phase="Phase 5"
            icon="i-lucide-bot"
            :description="
              agent
                ? `${agent.decisions_today} decisions, ${agent.proposals_today} proposals today.`
                : 'Live agent decision feed.'
            "
          />
          <FeaturePlaceholder
            title="Strategy performance"
            phase="Phase 8"
            icon="i-lucide-workflow"
            description="Per-strategy return, win rate and health."
          />
        </div>
      </section>
    </template>
  </div>
</template>
