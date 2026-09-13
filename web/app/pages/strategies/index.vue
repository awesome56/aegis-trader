<script setup lang="ts">
import type { OrderSide } from '~/types/order'
import type { SignalDirection } from '~/types/market'
import {
  useEvaluateStrategies,
  useSetStrategyEnabled,
  useStrategies,
  useStrategySignals,
} from '~/composables/useStrategies'
import { formatDateTime } from '~/utils/dates'
import { signalDirectionToSide } from '~/utils/strategy'

useHead({ title: 'Strategies' })

const strategiesQuery = useStrategies()
const setEnabled = useSetStrategyEnabled()
const evaluateStrategies = useEvaluateStrategies()

const strategies = computed(() => strategiesQuery.data.value ?? [])

const timeframeFilter = ref('')
const symbolFilter = ref('')
const directionFilter = ref<SignalDirection | ''>('')
const strategyFilter = ref('')
const page = ref(1)
const pageSize = 25

const signalParams = computed(() => ({
  page: page.value,
  pageSize,
  symbol: symbolFilter.value.trim() || undefined,
  direction: directionFilter.value || undefined,
  timeframe: timeframeFilter.value || undefined,
  strategy_id: strategyFilter.value || undefined,
}))

const signalsQuery = useStrategySignals(signalParams)
const signals = computed(() => signalsQuery.data.value?.items ?? [])
const signalTotal = computed(() => signalsQuery.data.value?.total ?? 0)
const signalPageCount = computed(() => Math.max(1, Math.ceil(signalTotal.value / pageSize)))

watch([symbolFilter, directionFilter, timeframeFilter, strategyFilter], () => {
  page.value = 1
})

const expanded = ref<Record<string, boolean>>({})
function toggleEvidence(id: string): void {
  expanded.value = { ...expanded.value, [id]: !expanded.value[id] }
}

const DIRECTION_OPTIONS: SignalDirection[] = ['LONG', 'SHORT', 'NEUTRAL']
const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d', '1w']

const dialog = reactive({ open: false, strategyId: '', strategyName: '', enabled: false })
const actionError = ref<string | null>(null)

function openToggle(id: string, name: string, enabled: boolean): void {
  actionError.value = null
  dialog.strategyId = id
  dialog.strategyName = name
  dialog.enabled = enabled
  dialog.open = true
}

async function confirmToggle(): Promise<void> {
  actionError.value = null
  try {
    await setEnabled.mutateAsync({ id: dialog.strategyId, enabled: !dialog.enabled })
    dialog.open = false
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : 'Failed to update strategy.'
  }
}

const evaluateForm = reactive({ symbol: '', timeframe: '1d', strategyId: '' })
const evaluateResults = ref<import('~/types/strategy').StrategyEvaluation[] | null>(null)
const evaluateError = ref<string | null>(null)

async function runEvaluation(): Promise<void> {
  evaluateError.value = null
  evaluateResults.value = null
  try {
    evaluateResults.value = await evaluateStrategies.mutateAsync({
      symbol: evaluateForm.symbol.trim().toUpperCase(),
      timeframe: evaluateForm.timeframe || undefined,
      strategy_ids: evaluateForm.strategyId ? [evaluateForm.strategyId] : undefined,
    })
  } catch (error) {
    evaluateError.value = error instanceof Error ? error.message : 'Evaluation failed.'
  }
}

function proposalLink(symbol: string, direction: SignalDirection, signalId: string, confidence: string | number): string | null {
  const side: OrderSide | null = signalDirectionToSide(direction)
  if (!side) return null
  const query = new URLSearchParams({ symbol, side, signal: signalId, confidence: String(confidence) })
  return `/agent/proposals/new?${query.toString()}`
}
</script>

<template>
  <div>
    <PageHeader
      title="Strategies"
      subtitle="Deterministic signal engines. Enabling a strategy never places a trade."
      eyebrow="Strategy engine"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="strategiesQuery.isLoading.value" @click="strategiesQuery.refetch(); signalsQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="strategiesQuery.isError.value"
      title="Strategies unavailable"
      message="The strategy API did not respond. Check the backend connection and retry."
      @retry="strategiesQuery.refetch()"
    />

    <template v-else>
      <div v-if="actionError" class="mb-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
        {{ actionError }}
      </div>

      <section class="rounded-lg border border-default bg-elevated/30 p-4">
        <h2 class="text-sm font-semibold text-highlighted">Registered strategies</h2>
        <LoadingSkeleton v-if="strategiesQuery.isLoading.value" class="mt-3" :rows="3" />
        <div v-else-if="strategies.length" class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Strategy</th>
                <th class="pb-2 font-medium">Type</th>
                <th class="pb-2 font-medium">Timeframe</th>
                <th class="pb-2 text-right font-medium">Signals</th>
                <th class="pb-2 text-right font-medium">Last Signal</th>
                <th class="pb-2 text-right font-medium">State</th>
                <th class="pb-2 text-right font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="strategy in strategies" :key="strategy.id" class="border-t border-default hover:bg-elevated/40">
                <td class="py-2">
                  <NuxtLink :to="`/strategies/${strategy.id}`" class="hover:underline">
                    <span class="font-medium text-highlighted">{{ strategy.name }}</span>
                    <span class="num ml-2 text-[11px] text-muted">{{ strategy.key }}</span>
                  </NuxtLink>
                  <p v-if="strategy.description" class="mt-0.5 max-w-md truncate text-[11px] text-muted">{{ strategy.description }}</p>
                </td>
                <td class="py-2 text-muted">{{ strategy.strategy_type.replaceAll('_', ' ') }}</td>
                <td class="num py-2 text-muted">{{ strategy.timeframe }}</td>
                <td class="num py-2 text-right text-default">{{ strategy.signal_count }}</td>
                <td class="py-2 text-right text-muted">{{ formatDateTime(strategy.last_signal_at) }}</td>
                <td class="py-2 text-right">
                  <StatusBadge :label="strategy.is_enabled ? 'ENABLED' : 'DISABLED'" :tone="strategy.is_enabled ? 'success' : 'neutral'" dot />
                </td>
                <td class="py-2 text-right">
                  <UButton
                    color="neutral"
                    variant="outline"
                    size="xs"
                    :disabled="setEnabled.isPending.value"
                    @click="openToggle(strategy.id, strategy.name, strategy.is_enabled)"
                  >
                    {{ strategy.is_enabled ? 'Disable' : 'Enable' }}
                  </UButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="No strategies registered" icon="i-lucide-workflow" />
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <div class="flex flex-wrap items-end justify-between gap-3">
          <h2 class="text-sm font-semibold text-highlighted">On-demand evaluation</h2>
          <span class="rounded bg-sky-500/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-sky-300">
            Analysis only — no trade or order will be created
          </span>
        </div>
        <div class="mt-3 flex flex-wrap items-end gap-2">
          <div>
            <label class="mb-1 block text-[11px] text-muted" for="eval-symbol">Symbol</label>
            <UInput id="eval-symbol" v-model="evaluateForm.symbol" placeholder="AAPL" class="w-32" />
          </div>
          <div>
            <label class="mb-1 block text-[11px] text-muted" for="eval-timeframe">Timeframe</label>
            <select id="eval-timeframe" v-model="evaluateForm.timeframe" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
              <option v-for="tf in TIMEFRAMES" :key="tf" :value="tf">{{ tf }}</option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-[11px] text-muted" for="eval-strategy">Strategy</label>
            <select id="eval-strategy" v-model="evaluateForm.strategyId" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
              <option value="">All enabled</option>
              <option v-for="strategy in strategies" :key="strategy.id" :value="strategy.id">{{ strategy.name }}</option>
            </select>
          </div>
          <UButton color="neutral" size="sm" icon="i-lucide-play" :disabled="!evaluateForm.symbol.trim()" :loading="evaluateStrategies.isPending.value" @click="runEvaluation">
            Run analysis
          </UButton>
        </div>

        <p v-if="evaluateError" class="mt-2 text-xs text-down">{{ evaluateError }}</p>
        <div v-else-if="evaluateResults" class="mt-3 space-y-2">
          <p v-if="!evaluateResults.length" class="text-xs text-muted">No strategies evaluated (none enabled).</p>
          <div v-for="(result, index) in evaluateResults" :key="index" class="rounded border border-default bg-elevated/20 p-3">
            <div class="flex items-center justify-between">
              <span class="text-xs text-default">{{ result.strategy_name }} · {{ result.timeframe }}</span>
              <StatusBadge :label="result.status.replaceAll('_', ' ')" :tone="result.status === 'SIGNAL' ? 'success' : result.status === 'STALE_DATA' ? 'warning' : 'neutral'" />
            </div>
            <p class="mt-1 text-[11px] text-muted">{{ result.reason }}</p>
            <div v-if="result.signal" class="mt-2">
              <div class="flex flex-wrap items-center gap-2 text-xs">
                <SignalDirectionBadge :direction="result.signal.direction" />
                <span class="text-muted">confidence</span>
                <span class="num text-default">{{ result.signal.confidence }}</span>
                <span class="text-muted">strength</span>
                <span class="num text-default">{{ result.signal.strength }}</span>
                <span v-if="result.signal.market_regime" class="text-muted">regime {{ result.signal.market_regime.replaceAll('_', ' ') }}</span>
              </div>
              <SignalEvidenceTable class="mt-2" :indicators="result.signal.indicators" />
            </div>
            <p v-else class="mt-2 text-[11px] text-muted">No signal generated. This is not an error.</p>
          </div>
        </div>
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-sm font-semibold text-highlighted">Strategy signals</h2>
          <span class="text-[11px] text-muted">{{ signalTotal }} signals</span>
        </div>
        <div class="mt-3 flex flex-wrap items-end gap-2">
          <UInput v-model="symbolFilter" placeholder="Symbol" class="w-28" />
          <select v-model="strategyFilter" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
            <option value="">All strategies</option>
            <option v-for="strategy in strategies" :key="strategy.id" :value="strategy.id">{{ strategy.name }}</option>
          </select>
          <select v-model="directionFilter" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
            <option value="">All directions</option>
            <option v-for="option in DIRECTION_OPTIONS" :key="option" :value="option">{{ option }}</option>
          </select>
          <select v-model="timeframeFilter" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
            <option value="">All timeframes</option>
            <option v-for="tf in TIMEFRAMES" :key="tf" :value="tf">{{ tf }}</option>
          </select>
        </div>

        <LoadingSkeleton v-if="signalsQuery.isLoading.value" class="mt-3" :rows="4" />
        <div v-else-if="signals.length" class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Time</th>
                <th class="pb-2 font-medium">Symbol</th>
                <th class="pb-2 font-medium">Strategy</th>
                <th class="pb-2 font-medium">TF</th>
                <th class="pb-2 font-medium">Direction</th>
                <th class="pb-2 text-right font-medium">Strength</th>
                <th class="pb-2 text-right font-medium">Conf.</th>
                <th class="pb-2 font-medium">Regime</th>
                <th class="pb-2 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="signal in signals" :key="signal.id">
                <tr class="border-t border-default hover:bg-elevated/40">
                  <td class="py-2 text-muted">{{ formatDateTime(signal.signal_time) }}</td>
                  <td class="py-2"><SymbolBadge :symbol="signal.symbol" size="sm" /></td>
                  <td class="py-2 text-muted">{{ signal.strategy_name ?? signal.strategy_key ?? '—' }}</td>
                  <td class="num py-2 text-muted">{{ signal.timeframe }}</td>
                  <td class="py-2"><SignalDirectionBadge :direction="signal.direction" /></td>
                  <td class="num py-2 text-right text-default">{{ signal.strength }}</td>
                  <td class="py-2 text-right"><PercentageValue :value="signal.confidence" /></td>
                  <td class="py-2 text-muted">{{ signal.market_regime?.replaceAll('_', ' ') ?? '—' }}</td>
                  <td class="py-2 text-right">
                    <div class="flex justify-end gap-1">
                      <UButton color="neutral" variant="ghost" size="xs" @click="toggleEvidence(signal.id)">
                        Evidence
                      </UButton>
                      <UButton
                        v-if="proposalLink(signal.symbol, signal.direction, signal.id, signal.confidence)"
                        color="primary"
                        variant="outline"
                        size="xs"
                        :to="proposalLink(signal.symbol, signal.direction, signal.id, signal.confidence)!"
                      >
                        Create Proposal
                      </UButton>
                    </div>
                  </td>
                </tr>
                <tr v-if="expanded[signal.id]" class="border-t border-default">
                  <td colspan="9" class="bg-elevated/10 p-3">
                    <SignalEvidenceTable :indicators="signal.indicators" title="Signal evidence" />
                    <p class="mt-2 text-[11px] text-muted">
                      data {{ formatDateTime(signal.data_timestamp) }} · expires {{ formatDateTime(signal.expires_at) }}
                    </p>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="No signals" message="No signals matched the current filters." icon="i-lucide-activity" />

        <div v-if="signalPageCount > 1" class="mt-3 flex items-center justify-between text-xs text-muted">
          <span>Page {{ page }} of {{ signalPageCount }}</span>
          <div class="flex gap-1">
            <UButton color="neutral" variant="outline" size="xs" :disabled="page <= 1" @click="page -= 1">Prev</UButton>
            <UButton color="neutral" variant="outline" size="xs" :disabled="page >= signalPageCount" @click="page += 1">Next</UButton>
          </div>
        </div>
      </section>
    </template>

    <ConfirmationDialog
      v-model:open="dialog.open"
      :title="dialog.enabled ? 'Disable strategy' : 'Enable strategy'"
      :description="dialog.enabled
        ? `${dialog.strategyName} will stop being evaluated on the schedule.`
        : `${dialog.strategyName} will resume scheduled evaluation.`"
      :consequences="dialog.enabled
        ? ['Scheduled evaluation stops', 'Historical signals remain available', 'Existing proposals, orders and positions are unchanged']
        : ['Scheduled evaluations resume', 'No trades or orders are placed automatically', 'Current positions are unchanged']"
      :tone="dialog.enabled ? 'danger' : 'default'"
      :confirm-label="dialog.enabled ? 'Disable' : 'Enable'"
      :loading="setEnabled.isPending.value"
      @confirm="confirmToggle"
    />
  </div>
</template>
