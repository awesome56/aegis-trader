<script setup lang="ts">
import { useSetStrategyEnabled, useStrategy } from '~/composables/useStrategies'
import { formatDateTime } from '~/utils/dates'

const route = useRoute()
const strategyId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Strategy ${strategyId.value}` })

const strategyQuery = useStrategy(strategyId)
const setEnabled = useSetStrategyEnabled()

const strategy = computed(() => strategyQuery.data.value ?? null)
const latestSignal = computed(() => strategy.value?.recent_signals[0] ?? null)

const dialog = reactive({ open: false })
const actionError = ref<string | null>(null)

async function confirmToggle(): Promise<void> {
  if (!strategy.value) return
  actionError.value = null
  try {
    await setEnabled.mutateAsync({ id: strategy.value.id, enabled: !strategy.value.is_enabled })
    dialog.open = false
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : 'Failed to update strategy.'
  }
}

const expanded = ref<Record<string, boolean>>({})
function toggle(id: string): void {
  expanded.value = { ...expanded.value, [id]: !expanded.value[id] }
}

const parameterRows = computed(() =>
  Object.entries(strategy.value?.parameters ?? {}).map(([key, value]) => ({
    key,
    label: key.replaceAll('_', ' '),
    value: typeof value === 'object' ? JSON.stringify(value) : String(value),
  })),
)
</script>

<template>
  <div>
    <PageHeader
      :title="strategy ? strategy.name : `Strategy ${strategyId}`"
      :subtitle="strategy?.description ?? 'Strategy configuration and signals.'"
      eyebrow="Strategy engine"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-arrow-left" to="/strategies">
          All strategies
        </UButton>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="strategyQuery.isLoading.value" @click="strategyQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="strategyQuery.isError.value"
      title="Strategy unavailable"
      message="This strategy could not be loaded. It may not exist, or the backend is unreachable."
      @retry="strategyQuery.refetch()"
    />
    <LoadingSkeleton v-else-if="strategyQuery.isLoading.value" :rows="6" />

    <template v-else-if="strategy">
      <div v-if="actionError" class="mb-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
        {{ actionError }}
      </div>

      <div class="mb-3 flex flex-wrap items-center gap-2">
        <StatusBadge :label="strategy.is_enabled ? 'ENABLED' : 'DISABLED'" :tone="strategy.is_enabled ? 'success' : 'neutral'" dot />
        <StatusBadge :label="strategy.strategy_type.replaceAll('_', ' ')" tone="neutral" />
        <StatusBadge :label="strategy.timeframe" tone="neutral" />
        <UButton
          color="neutral"
          variant="outline"
          size="xs"
          :loading="setEnabled.isPending.value"
          @click="dialog.open = true"
        >
          {{ strategy.is_enabled ? 'Disable strategy' : 'Enable strategy' }}
        </UButton>
      </div>

      <section class="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="rounded-lg border border-default bg-elevated/30 p-4">
          <h2 class="text-sm font-semibold text-highlighted">Configuration</h2>
          <dl class="mt-3 space-y-2 text-xs">
            <div class="flex justify-between"><dt class="text-muted">Key</dt><dd class="num text-default">{{ strategy.key }}</dd></div>
            <div class="flex justify-between"><dt class="text-muted">Priority</dt><dd class="num text-default">{{ strategy.priority }}</dd></div>
            <div class="flex justify-between"><dt class="text-muted">Asset classes</dt><dd class="text-default">{{ strategy.asset_classes?.join(', ') ?? '—' }}</dd></div>
            <div class="flex justify-between"><dt class="text-muted">Signals recorded</dt><dd class="num text-default">{{ strategy.signal_count }}</dd></div>
            <div class="flex justify-between"><dt class="text-muted">Last signal</dt><dd class="text-default">{{ formatDateTime(strategy.last_signal_at) }}</dd></div>
          </dl>
          <div v-if="parameterRows.length" class="mt-3 border-t border-default pt-3">
            <p class="text-[11px] uppercase tracking-wide text-muted">Parameters</p>
            <dl class="mt-2 space-y-1 text-xs">
              <div v-for="row in parameterRows" :key="row.key" class="flex justify-between">
                <dt class="capitalize text-muted">{{ row.label }}</dt>
                <dd class="num text-default">{{ row.value }}</dd>
              </div>
            </dl>
          </div>
        </div>

        <div class="rounded-lg border border-default bg-elevated/30 p-4 xl:col-span-2">
          <h2 class="text-sm font-semibold text-highlighted">How this strategy currently sees the market</h2>
          <div v-if="latestSignal" class="mt-3">
            <div class="flex flex-wrap items-center gap-2 text-xs">
              <SymbolBadge :symbol="latestSignal.symbol" size="sm" />
              <SignalDirectionBadge :direction="latestSignal.direction" />
              <span class="text-muted">confidence</span><span class="num text-default">{{ latestSignal.confidence }}</span>
              <span class="text-muted">strength</span><span class="num text-default">{{ latestSignal.strength }}</span>
              <span v-if="latestSignal.market_regime" class="text-muted">regime {{ latestSignal.market_regime.replaceAll('_', ' ') }}</span>
              <span class="text-muted">· {{ formatDateTime(latestSignal.signal_time) }}</span>
            </div>
            <SignalEvidenceTable class="mt-3" :indicators="latestSignal.indicators" title="Indicators" />
          </div>
          <EmptyState v-else class="mt-3" title="No recent signal" message="This strategy has not produced a signal recently." icon="i-lucide-activity" />
        </div>
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <h2 class="text-sm font-semibold text-highlighted">Recent signals</h2>
        <div v-if="strategy.recent_signals.length" class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Time</th>
                <th class="pb-2 font-medium">Symbol</th>
                <th class="pb-2 font-medium">Direction</th>
                <th class="pb-2 text-right font-medium">Strength</th>
                <th class="pb-2 text-right font-medium">Confidence</th>
                <th class="pb-2 font-medium">Regime</th>
                <th class="pb-2 text-right font-medium"></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="signal in strategy.recent_signals" :key="signal.id">
                <tr class="border-t border-default">
                  <td class="py-2 text-muted">{{ formatDateTime(signal.signal_time) }}</td>
                  <td class="py-2"><SymbolBadge :symbol="signal.symbol" size="sm" /></td>
                  <td class="py-2"><SignalDirectionBadge :direction="signal.direction" /></td>
                  <td class="num py-2 text-right text-default">{{ signal.strength }}</td>
                  <td class="num py-2 text-right text-default">{{ signal.confidence }}</td>
                  <td class="py-2 text-muted">{{ signal.market_regime?.replaceAll('_', ' ') ?? '—' }}</td>
                  <td class="py-2 text-right">
                    <UButton color="neutral" variant="ghost" size="xs" @click="toggle(signal.id)">Evidence</UButton>
                  </td>
                </tr>
                <tr v-if="expanded[signal.id]" class="border-t border-default">
                  <td colspan="7" class="bg-elevated/10 p-3">
                    <SignalEvidenceTable :indicators="signal.indicators" title="Signal evidence" />
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="No signals recorded" icon="i-lucide-activity" />
      </section>
    </template>

    <ConfirmationDialog
      v-model:open="dialog.open"
      :title="strategy?.is_enabled ? 'Disable strategy' : 'Enable strategy'"
      :description="strategy?.is_enabled
        ? `${strategy?.name} will stop being evaluated on the schedule.`
        : `${strategy?.name} will resume scheduled evaluation.`"
      :consequences="strategy?.is_enabled
        ? ['Scheduled evaluation stops', 'Historical signals remain available', 'Existing proposals, orders and positions are unchanged']
        : ['Scheduled evaluations resume', 'No trades or orders are placed automatically', 'Current positions are unchanged']"
      :tone="strategy?.is_enabled ? 'danger' : 'default'"
      :confirm-label="strategy?.is_enabled ? 'Disable' : 'Enable'"
      :loading="setEnabled.isPending.value"
      @confirm="confirmToggle"
    />
  </div>
</template>
