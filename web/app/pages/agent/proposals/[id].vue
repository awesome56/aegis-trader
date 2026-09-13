<script setup lang="ts">
import type { ProposalStatus } from '~/types/agent'
import type { AuditStage } from '~/components/AuditTimeline.vue'
import {
  useCancelProposal,
  useEvaluateProposal,
  useExecuteProposal,
  useProposalDetail,
} from '~/composables/useProposals'
import { formatCurrency } from '~/utils/currency'
import { formatDateTime } from '~/utils/dates'
import { formatPercentage } from '~/utils/percentage'

const route = useRoute()
const proposalId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Proposal ${proposalId.value}` })

const detailQuery = useProposalDetail(proposalId)
const evaluateProposal = useEvaluateProposal()
const executeProposal = useExecuteProposal()
const cancelProposal = useCancelProposal()

const detail = computed(() => detailQuery.data.value ?? null)
const proposal = computed(() => detail.value?.proposal ?? null)
const evaluations = computed(() => detail.value?.evaluations ?? [])
const orders = computed(() => detail.value?.orders ?? [])
const executions = computed(() => detail.value?.executions ?? [])

const EVALUATABLE: ProposalStatus[] = ['DRAFT', 'PENDING', 'PENDING_RISK', 'RISK_APPROVED', 'APPROVED']
const EXECUTABLE: ProposalStatus[] = ['RISK_APPROVED', 'READY_FOR_EXECUTION', 'APPROVED']
const CANCELLABLE: ProposalStatus[] = ['DRAFT', 'PENDING', 'PENDING_RISK', 'RISK_APPROVED', 'APPROVED', 'READY_FOR_EXECUTION']

const canEvaluate = computed(() => !!proposal.value && EVALUATABLE.includes(proposal.value.status))
const canExecute = computed(() => !!proposal.value && EXECUTABLE.includes(proposal.value.status))
const canCancel = computed(() => !!proposal.value && CANCELLABLE.includes(proposal.value.status))

const evaluateError = ref<string | null>(null)
const outcome = ref<import('~/types/agent').ExecutionOutcome | null>(null)
const actionError = ref<string | null>(null)
const dialog = reactive({ open: false, action: 'execute' as 'execute' | 'cancel', loading: false })

async function evaluate(): Promise<void> {
  evaluateError.value = null
  actionError.value = null
  outcome.value = null
  try {
    await evaluateProposal.mutateAsync(proposalId.value)
  } catch (error) {
    evaluateError.value = error instanceof Error ? error.message : 'Risk evaluation failed.'
  }
}

function openDialog(action: 'execute' | 'cancel'): void {
  actionError.value = null
  dialog.action = action
  dialog.open = true
}

async function runAction(): Promise<void> {
  dialog.loading = true
  actionError.value = null
  try {
    if (dialog.action === 'execute') {
      outcome.value = await executeProposal.mutateAsync(proposalId.value)
    } else {
      await cancelProposal.mutateAsync(proposalId.value)
    }
    dialog.open = false
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : 'Action failed.'
  } finally {
    dialog.loading = false
  }
}

const summary = computed(() => {
  const p = proposal.value
  if (!p) return []
  return [
    { label: 'Side', value: p.action },
    { label: 'Order type', value: p.order_type.replace('_', ' ') },
    { label: 'Requested quantity', value: String(p.proposed_quantity) },
    { label: 'Requested notional', value: p.requested_notional === null ? '—' : formatCurrency(p.requested_notional, { currency: 'USD' }) },
    { label: 'Proposed entry', value: p.entry_price === null ? '—' : formatCurrency(p.entry_price, { currency: 'USD' }) },
    { label: 'Stop loss', value: p.stop_loss === null ? '—' : formatCurrency(p.stop_loss, { currency: 'USD' }) },
    { label: 'Take profit', value: p.take_profit === null ? '—' : formatCurrency(p.take_profit, { currency: 'USD' }) },
    { label: 'Source', value: p.source },
    { label: 'Confidence', value: formatPercentage(p.confidence) },
    { label: 'Time horizon', value: p.time_horizon.replace('_', ' ') },
    { label: 'Created', value: formatDateTime(p.created_at) },
    { label: 'Expires', value: formatDateTime(p.expires_at) },
  ]
})

const stages = computed<AuditStage[]>(() => {
  const p = proposal.value
  if (!p) return []
  const decision = evaluations.value[0]?.decision
  const approved = p.status === 'RISK_APPROVED' || p.status === 'READY_FOR_EXECUTION' || p.status === 'EXECUTING' || p.status === 'EXECUTED'
  const rejected = p.status === 'RISK_REJECTED' || p.status === 'REJECTED' || p.status === 'FAILED'
  const started = !!p.executed_at || p.status === 'EXECUTING' || approved && (orders.value.length > 0)

  return [
    { key: 'created', label: 'Proposal created', status: 'done', at: formatDateTime(p.created_at) },
    evaluations.value.length
      ? { key: 'evaluation', label: 'Risk evaluation', status: 'done', at: formatDateTime(evaluations.value[0]!.evaluated_at), detail: `Decision: ${decision}` }
      : { key: 'evaluation', label: 'Risk evaluation', status: 'pending' },
    { key: 'decision', label: 'Risk approved / rejected', status: rejected ? 'failed' : approved ? 'done' : 'pending', detail: rejected ? p.failure_reason ?? undefined : undefined },
    { key: 'executing', label: 'Execution started', status: started ? 'done' : 'pending', at: p.executed_at ? formatDateTime(p.executed_at) : null },
    evaluations.value.length > 1
      ? { key: 'revalidation', label: 'Final risk revalidation', status: 'done', detail: `Decision: ${evaluations.value[evaluations.value.length - 1]!.decision}` }
      : { key: 'revalidation', label: 'Final risk revalidation', status: p.status === 'EXECUTING' ? 'active' : 'pending' },
    orders.value.length
      ? { key: 'order', label: 'Broker order', status: 'done', at: formatDateTime(orders.value[0]!.created_at) }
      : { key: 'order', label: 'Broker order', status: p.status === 'EXECUTING' ? 'active' : 'pending' },
    executions.value.length
      ? { key: 'execution', label: 'Execution / fill', status: 'done', at: formatDateTime(executions.value[0]!.executed_at) }
      : { key: 'execution', label: 'Execution / fill', status: 'pending' },
    { key: 'position', label: 'Position updated', status: p.status === 'EXECUTED' ? 'done' : 'pending' },
    { key: 'portfolio', label: 'Portfolio updated', status: p.status === 'EXECUTED' ? 'done' : 'pending' },
  ]
})

const revalidationRejected = computed(
  () => outcome.value !== null && !outcome.value.executed && outcome.value.final_decision === 'REJECTED',
)
</script>

<template>
  <div>
    <PageHeader
      :title="proposal ? `${proposal.symbol} proposal` : `Proposal ${proposalId}`"
      subtitle="Proposal → risk evaluation → execution → order → position."
      eyebrow="Execution pipeline"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-arrow-left" to="/agent/proposals">
          All proposals
        </UButton>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="detailQuery.isLoading.value" @click="detailQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="detailQuery.isError.value"
      title="Proposal unavailable"
      message="This proposal could not be loaded. It may not exist, or the backend is unreachable."
      @retry="detailQuery.refetch()"
    />
    <LoadingSkeleton v-else-if="detailQuery.isLoading.value" :rows="8" />

    <template v-else-if="proposal">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <ProposalStatusBadge :status="proposal.status" />
        <StatusBadge :label="proposal.source" tone="neutral" />
        <span v-if="proposal.failure_reason" class="text-xs text-down">{{ proposal.failure_reason }}</span>
      </div>

      <div v-if="evaluateError" class="mb-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
        {{ evaluateError }}
      </div>
      <div v-if="actionError" class="mb-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
        {{ actionError }}
      </div>

      <div
        v-if="outcome"
        class="mb-3 rounded-md border px-3 py-2 text-xs"
        :class="outcome.executed ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-amber-500/40 bg-amber-500/10 text-amber-300'"
      >
        <template v-if="outcome.executed">
          Proposal executed — broker order accepted.
        </template>
        <template v-else>
          No order submitted: {{ outcome.reason ?? 'execution did not complete' }}
        </template>
      </div>

      <div v-if="revalidationRejected" class="mb-3 rounded-lg border border-amber-500/40 bg-amber-500/5 p-3 text-xs">
        <p class="font-medium text-amber-300">Final risk revalidation rejected this execution</p>
        <dl class="mt-2 space-y-1 text-muted">
          <div class="flex justify-between"><dt>Initial risk evaluation</dt><dd class="text-default">APPROVED</dd></div>
          <div class="flex justify-between"><dt>Final risk revalidation</dt><dd class="text-down">REJECTED</dd></div>
          <div class="flex justify-between"><dt>Reason</dt><dd class="text-default">{{ outcome?.reason }}</dd></div>
          <div class="flex justify-between"><dt>Execution</dt><dd class="text-default">NO ORDER SUBMITTED</dd></div>
        </dl>
        <p class="mt-2 text-[11px] text-muted">
          This is an expected safety outcome: market, portfolio or trading state changed after initial approval.
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <UButton color="neutral" variant="solid" size="sm" icon="i-lucide-shield-check" :disabled="!canEvaluate" :loading="evaluateProposal.isPending.value" @click="evaluate">
          Evaluate Risk
        </UButton>
        <UButton color="primary" size="sm" icon="i-lucide-play" :disabled="!canExecute" @click="openDialog('execute')">
          Execute Proposal
        </UButton>
        <UButton color="warning" variant="outline" size="sm" icon="i-lucide-x" :disabled="!canCancel" @click="openDialog('cancel')">
          Cancel Proposal
        </UButton>
      </div>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="rounded-lg border border-default bg-elevated/30 p-4 xl:col-span-2">
          <h2 class="text-sm font-semibold text-highlighted">Proposal summary</h2>
          <dl class="mt-3 grid grid-cols-2 gap-y-3 text-xs lg:grid-cols-3">
            <template v-for="row in summary" :key="row.label">
              <dt class="text-muted">{{ row.label }}</dt>
              <dd class="text-right text-default">{{ row.value }}</dd>
            </template>
          </dl>
          <p v-if="proposal.strategy_signal_id" class="mt-3 text-[11px] text-muted">
            Strategy signal reference: <span class="num">{{ proposal.strategy_signal_id }}</span>
          </p>
          <p v-if="proposal.reasoning_summary" class="mt-2 text-xs text-muted">{{ proposal.reasoning_summary }}</p>
        </div>

        <div class="rounded-lg border border-default bg-elevated/30 p-4">
          <h2 class="text-sm font-semibold text-highlighted">Audit timeline</h2>
          <div class="mt-3">
            <AuditTimeline :stages="stages" />
          </div>
        </div>
      </section>

      <section v-if="evaluations.length" class="mt-4 space-y-4">
        <RiskEvaluationPanel v-for="evaluation in evaluations" :key="evaluation.id" :evaluation="evaluation" />
      </section>
      <section v-else class="mt-4">
        <EmptyState title="No risk evaluation yet" message="Run Evaluate Risk to produce a deterministic verdict." icon="i-lucide-shield" />
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <h2 class="text-sm font-semibold text-highlighted">Broker orders</h2>
        <div v-if="orders.length" class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Order</th>
                <th class="pb-2 font-medium">Side</th>
                <th class="pb-2 font-medium">Type</th>
                <th class="pb-2 text-right font-medium">Qty</th>
                <th class="pb-2 text-right font-medium">Filled</th>
                <th class="pb-2 text-right font-medium">Avg fill</th>
                <th class="pb-2 text-right font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id" class="border-t border-default">
                <td class="py-2">
                  <NuxtLink :to="`/orders/${order.id}`" class="num text-muted hover:underline">
                    {{ order.id.slice(0, 8) }}
                  </NuxtLink>
                </td>
                <td class="py-2"><StatusBadge :label="order.side" :tone="order.side === 'BUY' ? 'success' : 'danger'" /></td>
                <td class="py-2 text-muted">{{ order.order_type.replace('_', ' ') }}</td>
                <td class="num py-2 text-right text-default">{{ order.quantity }}</td>
                <td class="num py-2 text-right text-default">{{ order.filled_quantity }}</td>
                <td class="py-2 text-right"><PriceValue :value="order.average_fill_price" /></td>
                <td class="py-2 text-right"><OrderStatusBadge :status="order.status" /></td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="No broker order" message="An order appears after an approved proposal is executed." icon="i-lucide-receipt" />
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <h2 class="text-sm font-semibold text-highlighted">Executions</h2>
        <div v-if="executions.length" class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Execution</th>
                <th class="pb-2 text-right font-medium">Qty</th>
                <th class="pb-2 text-right font-medium">Price</th>
                <th class="pb-2 text-right font-medium">Commission</th>
                <th class="pb-2 text-right font-medium">Executed</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="execution in executions" :key="execution.id" class="border-t border-default">
                <td class="py-2 text-muted"><span class="num">{{ execution.id.slice(0, 8) }}</span></td>
                <td class="num py-2 text-right text-default">{{ execution.quantity }}</td>
                <td class="py-2 text-right"><PriceValue :value="execution.price" /></td>
                <td class="num py-2 text-right text-muted">{{ execution.commission }}</td>
                <td class="py-2 text-right text-muted">{{ formatDateTime(execution.executed_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="No executions" message="Fills appear here once the broker executes the order." icon="i-lucide-activity" />
      </section>
    </template>

    <ConfirmationDialog
      v-model:open="dialog.open"
      :title="dialog.action === 'execute' ? 'Execute proposal' : 'Cancel proposal'"
      :description="dialog.action === 'execute'
        ? 'The backend will re-check current price, trading state, buying power and risk limits before submitting this order.'
        : 'This cancels the proposal. No broker order will be created.'"
      :consequences="dialog.action === 'execute'
        ? ['PAPER TRADING environment', 'Final risk revalidation runs immediately before submission', 'Initial approval does not guarantee execution']
        : ['Proposal becomes terminal', 'Existing orders or positions are unaffected']"
      :tone="dialog.action === 'execute' ? 'default' : 'danger'"
      :confirm-label="dialog.action === 'execute' ? 'Execute' : 'Cancel proposal'"
      :loading="dialog.loading"
      @confirm="runAction"
    />
  </div>
</template>
