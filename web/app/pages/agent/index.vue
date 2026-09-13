<script setup lang="ts">
import type { AgentDecisionRecord, AnalyzeInput } from '~/types/agent'
import {
  useAgentDecisions,
  useAgentRun,
  useAgentRuns,
  useAgentStatus,
  useCreateAgentRun,
} from '~/composables/useAgent'
import { formatDateTime } from '~/utils/dates'
import { formatPercentage } from '~/utils/percentage'

useHead({ title: 'Agent' })

const statusQuery = useAgentStatus()
const runsQuery = useAgentRuns({ page: 1, pageSize: 10 })
const decisionsQuery = useAgentDecisions({ page: 1, pageSize: 10 })
const createRun = useCreateAgentRun()

const status = computed(() => statusQuery.data.value ?? null)
const runs = computed(() => runsQuery.data.value?.items ?? [])
const decisions = computed(() => decisionsQuery.data.value?.items ?? [])

const form = reactive<AnalyzeInput>({
  symbol: 'AAPL',
  timeframe: '1h',
  mode: 'ANALYSIS_ONLY',
  prompt: '',
})
const errorMessage = ref<string | null>(null)
const activeRunId = ref('')
const activeRunQuery = useAgentRun(computed(() => activeRunId.value))
const activeRun = computed(() => activeRunQuery.data.value ?? null)

const activeDecision = computed<AgentDecisionRecord | null>(
  () => decisions.value.find((decision) => decision.agent_run_id === activeRunId.value) ?? null,
)

const expanded = ref<Record<string, boolean>>({})
function toggle(id: string): void {
  expanded.value = { ...expanded.value, [id]: !expanded.value[id] }
}

const providerConfigured = computed(
  () => !!status.value?.provider && status.value.provider_status !== 'NOT_CONFIGURED',
)

async function runAnalysis(): Promise<void> {
  errorMessage.value = null
  if (!form.symbol.trim()) {
    errorMessage.value = 'Symbol is required.'
    return
  }
  try {
    const run = await createRun.mutateAsync({
      symbol: form.symbol.trim().toUpperCase(),
      timeframe: form.timeframe,
      mode: form.mode,
      prompt: form.prompt?.trim() || undefined,
    })
    activeRunId.value = run.id
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Agent run failed.'
  }
}

const actionTone: Record<string, 'success' | 'danger' | 'neutral'> = {
  BUY: 'success',
  SELL: 'danger',
  HOLD: 'neutral',
}
const statusTone: Record<string, 'success' | 'info' | 'danger' | 'warning' | 'neutral'> = {
  COMPLETED: 'success',
  RUNNING: 'info',
  PENDING: 'neutral',
  FAILED: 'danger',
  CANCELLED: 'warning',
}

function evidenceRows(data: Record<string, unknown> | undefined): { key: string; value: string }[] {
  if (!data) return []
  return Object.entries(data)
    .filter(([, value]) => value === null || typeof value !== 'object')
    .map(([key, value]) => ({ key, value: String(value) }))
}
</script>

<template>
  <div>
    <PageHeader
      title="Agent"
      subtitle="TradingAnalysisAgent — analysis and proposal creation only. No execution."
      eyebrow="Intelligence"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="statusQuery.isLoading.value" @click="statusQuery.refetch(); runsQuery.refetch(); decisionsQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="statusQuery.isError.value"
      title="Agent unavailable"
      message="The agent API did not respond. Check the backend connection and retry."
      @retry="statusQuery.refetch()"
    />

    <template v-else>
      <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Provider" :value="status?.provider ?? '—'" :hint="status?.model ?? 'not configured'" :loading="statusQuery.isLoading.value" />
        <MetricCard label="Provider Status" :value="status?.provider_status ?? '—'" :hint="status?.default_mode" :loading="statusQuery.isLoading.value" />
        <MetricCard label="Running" :value="String(status?.running ?? 0)" :hint="`${status?.runs_today ?? 0} runs today`" :loading="statusQuery.isLoading.value" />
        <MetricCard label="Recent Failures" :value="String(status?.recent_failures ?? 0)" hint="last 24h" :loading="statusQuery.isLoading.value" />
      </section>

      <div v-if="!providerConfigured" class="mt-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
        No LLM provider is configured. Add one in Settings → AI Providers before running the agent.
      </div>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-highlighted">Analyze asset</h2>
          <span class="rounded bg-sky-500/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-sky-300">
            The agent can never place orders
          </span>
        </div>
        <div v-if="errorMessage" class="mt-2 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
          {{ errorMessage }}
        </div>
        <div class="mt-3 flex flex-wrap items-end gap-2">
          <div>
            <label class="mb-1 block text-[11px] text-muted" for="agent-symbol">Symbol</label>
            <UInput id="agent-symbol" v-model="form.symbol" placeholder="AAPL" class="w-24" />
          </div>
          <div>
            <label class="mb-1 block text-[11px] text-muted" for="agent-tf">Timeframe</label>
            <select id="agent-tf" v-model="form.timeframe" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
              <option v-for="tf in ['1m', '5m', '15m', '1h', '4h', '1d', '1w']" :key="tf" :value="tf">{{ tf }}</option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-[11px] text-muted" for="agent-mode">Mode</label>
            <select id="agent-mode" v-model="form.mode" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
              <option value="ANALYSIS_ONLY">Analysis Only</option>
              <option value="PROPOSE">Propose Trade</option>
            </select>
          </div>
          <div class="min-w-48 flex-1">
            <label class="mb-1 block text-[11px] text-muted" for="agent-prompt">Question (optional)</label>
            <UInput id="agent-prompt" v-model="form.prompt" placeholder="Look for a potential opportunity…" class="w-full" />
          </div>
          <UButton color="primary" size="sm" icon="i-lucide-sparkles" :disabled="!providerConfigured" :loading="createRun.isPending.value" @click="runAnalysis">
            Run analysis
          </UButton>
        </div>
        <p class="mt-2 text-[11px] text-muted">
          <strong>Analysis Only</strong> returns structured analysis and never creates a proposal.
          <strong>Propose Trade</strong> may create one DRAFT proposal which still requires manual risk evaluation and execution.
        </p>

        <div v-if="activeRun" class="mt-3 rounded border border-default bg-elevated/20 p-3">
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <StatusBadge :label="activeRun.status" :tone="statusTone[activeRun.status]" dot />
            <span class="text-muted">{{ activeRun.provider }}/{{ activeRun.model }}</span>
            <span class="text-muted">· {{ activeRun.mode }}</span>
            <span v-if="activeRun.tokens_used !== null" class="text-muted">· {{ activeRun.tokens_used }} tokens</span>
          </div>
          <p v-if="activeRun.error" class="mt-2 text-xs text-down">{{ activeRun.error }}</p>

          <div v-if="activeDecision" class="mt-3">
            <div class="flex flex-wrap items-center gap-2">
              <StatusBadge :label="activeDecision.action" :tone="actionTone[activeDecision.action] ?? 'neutral'" />
              <span class="text-xs text-muted">confidence</span>
              <span class="num text-sm text-highlighted">{{ formatPercentage(activeDecision.confidence) }}</span>
              <span v-if="activeDecision.market_regime" class="text-xs text-muted">· regime {{ activeDecision.market_regime.replaceAll('_', ' ') }}</span>
            </div>
            <p class="mt-2 text-xs text-default">{{ activeDecision.reasoning_summary }}</p>
            <div v-if="activeDecision.concerns?.length" class="mt-2">
              <p class="text-[11px] font-medium text-amber-400">Concerns</p>
              <ul class="mt-1 list-disc pl-4 text-[11px] text-muted">
                <li v-for="(concern, index) in activeDecision.concerns" :key="index">{{ concern }}</li>
              </ul>
            </div>
            <div v-if="activeDecision.evidence?.length" class="mt-2">
              <p class="text-[11px] font-medium text-muted">Evidence</p>
              <ul class="mt-1 space-y-1">
                <li v-for="(item, index) in activeDecision.evidence" :key="index" class="text-[11px] text-muted">
                  <span class="text-default">{{ item.type }}</span> · {{ item.source }}
                  <span v-if="item.direction"> · {{ item.direction }}</span>
                  <span v-if="item.confidence !== null && item.confidence !== undefined"> · conf {{ item.confidence }}</span>
                </li>
              </ul>
            </div>
            <div v-if="activeDecision.proposal_id" class="mt-3 rounded border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
              Proposal created (DRAFT) —
              <NuxtLink :to="`/agent/proposals/${activeDecision.proposal_id}`" class="underline">
                open proposal
              </NuxtLink>
              . It still requires manual risk evaluation and execution.
            </div>
          </div>
          <p v-else-if="activeRun.status === 'RUNNING' || activeRun.status === 'PENDING'" class="mt-2 text-xs text-muted">
            Analyzing {{ activeRun.symbols.join(', ') }}…
          </p>
        </div>
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <h2 class="text-sm font-semibold text-highlighted">Recent decisions</h2>
        <LoadingSkeleton v-if="decisionsQuery.isLoading.value" class="mt-3" :rows="3" />
        <div v-else-if="decisions.length" class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Time</th>
                <th class="pb-2 font-medium">Symbol</th>
                <th class="pb-2 font-medium">Action</th>
                <th class="pb-2 text-right font-medium">Confidence</th>
                <th class="pb-2 font-medium">Regime</th>
                <th class="pb-2 font-medium">Summary</th>
                <th class="pb-2 text-right font-medium">Proposal</th>
                <th class="pb-2 text-right font-medium"></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="decision in decisions" :key="decision.id">
                <tr class="border-t border-default">
                  <td class="py-2 text-muted">{{ formatDateTime(decision.created_at) }}</td>
                  <td class="py-2"><SymbolBadge :symbol="decision.symbol" size="sm" /></td>
                  <td class="py-2"><StatusBadge :label="decision.action" :tone="actionTone[decision.action] ?? 'neutral'" /></td>
                  <td class="py-2 text-right"><PercentageValue :value="decision.confidence" /></td>
                  <td class="py-2 text-muted">{{ decision.market_regime?.replaceAll('_', ' ') ?? '—' }}</td>
                  <td class="max-w-sm truncate py-2 text-muted">{{ decision.reasoning_summary ?? '—' }}</td>
                  <td class="py-2 text-right">
                    <NuxtLink v-if="decision.proposal_id" :to="`/agent/proposals/${decision.proposal_id}`" class="text-muted hover:text-highlighted">
                      open
                    </NuxtLink>
                    <span v-else class="text-muted">—</span>
                  </td>
                  <td class="py-2 text-right">
                    <UButton v-if="decision.evidence?.length" color="neutral" variant="ghost" size="xs" @click="toggle(decision.id)">
                      Evidence
                    </UButton>
                  </td>
                </tr>
                <tr v-if="expanded[decision.id]" class="border-t border-default">
                  <td colspan="8" class="bg-elevated/10 p-3">
                    <div v-for="(item, index) in decision.evidence" :key="index" class="mb-2">
                      <p class="text-[11px] text-default">
                        {{ item.type }} · {{ item.source }}
                        <span v-if="item.direction"> · {{ item.direction }}</span>
                      </p>
                      <table v-if="evidenceRows(item.data).length" class="mt-1 w-full max-w-sm text-left text-[11px]">
                        <tbody>
                          <tr v-for="row in evidenceRows(item.data)" :key="row.key" class="border-t border-default first:border-t-0">
                            <td class="py-0.5 pr-4 text-muted">{{ row.key }}</td>
                            <td class="num py-0.5 text-default">{{ row.value }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <p v-if="decision.concerns?.length" class="text-[11px] text-amber-400">Concerns: {{ decision.concerns.join('; ') }}</p>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="No agent decisions yet" message="Run an analysis to produce the first decision." icon="i-lucide-bot" />
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <h2 class="text-sm font-semibold text-highlighted">Recent runs</h2>
        <LoadingSkeleton v-if="runsQuery.isLoading.value" class="mt-3" :rows="3" />
        <div v-else-if="runs.length" class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Created</th>
                <th class="pb-2 font-medium">Symbol</th>
                <th class="pb-2 font-medium">Mode</th>
                <th class="pb-2 font-medium">Provider/Model</th>
                <th class="pb-2 text-right font-medium">Latency</th>
                <th class="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="run in runs" :key="run.id" class="border-t border-default">
                <td class="py-2 text-muted">{{ formatDateTime(run.created_at) }}</td>
                <td class="py-2 text-default">{{ run.symbols.join(', ') || '—' }}</td>
                <td class="py-2 text-muted">{{ run.mode }}</td>
                <td class="py-2 text-muted">{{ run.provider }}/{{ run.model }}</td>
                <td class="num py-2 text-right text-muted">{{ run.latency_ms === null ? '—' : `${run.latency_ms} ms` }}</td>
                <td class="py-2"><StatusBadge :label="run.status" :tone="statusTone[run.status]" dot /></td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="No agent runs yet" icon="i-lucide-workflow" />
      </section>
    </template>
  </div>
</template>
