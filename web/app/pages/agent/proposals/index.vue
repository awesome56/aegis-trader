<script setup lang="ts">
import type { ProposalStatus } from '~/types/agent'
import { useProposals } from '~/composables/useProposals'
import { formatDateTime } from '~/utils/dates'

useHead({ title: 'Trade Proposals' })

const STATUSES: ProposalStatus[] = [
  'DRAFT',
  'PENDING',
  'PENDING_RISK',
  'RISK_APPROVED',
  'READY_FOR_EXECUTION',
  'EXECUTING',
  'EXECUTED',
  'RISK_REJECTED',
  'EXPIRED',
  'CANCELLED',
  'FAILED',
]

const statusFilter = ref<ProposalStatus | ''>('')
const page = ref(1)
const pageSize = 25

const params = computed(() => ({
  page: page.value,
  pageSize,
  status: statusFilter.value || undefined,
}))

const proposalsQuery = useProposals(params)
const items = computed(() => proposalsQuery.data.value?.items ?? [])
const total = computed(() => proposalsQuery.data.value?.total ?? 0)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

watch(statusFilter, () => {
  page.value = 1
})

const sourceTone: Record<string, 'info' | 'neutral'> = { MANUAL: 'neutral', STRATEGY: 'info', AGENT: 'info' }
</script>

<template>
  <div>
    <PageHeader
      title="Trade Proposals"
      subtitle="Manual and strategy proposals gated by the deterministic Risk Engine."
      eyebrow="Execution pipeline"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="proposalsQuery.isLoading.value" @click="proposalsQuery.refetch()">
          Refresh
        </UButton>
        <UButton color="primary" size="sm" icon="i-lucide-plus" to="/agent/proposals/new">
          New Proposal
        </UButton>
      </template>
    </PageHeader>

    <div class="mb-3 flex flex-wrap items-center gap-2">
      <label class="text-xs text-muted" for="proposal-status-filter">Status</label>
      <select
        id="proposal-status-filter"
        v-model="statusFilter"
        class="rounded border border-default bg-elevated/40 px-2 py-1 text-xs text-default"
      >
        <option value="">All</option>
        <option v-for="status in STATUSES" :key="status" :value="status">
          {{ status.replaceAll('_', ' ') }}
        </option>
      </select>
      <span class="text-[11px] text-muted">{{ total }} proposals</span>
    </div>

    <ErrorState
      v-if="proposalsQuery.isError.value"
      title="Proposals unavailable"
      message="The proposal API did not respond. Check the backend connection and retry."
      @retry="proposalsQuery.refetch()"
    />

    <div v-else class="rounded-lg border border-default bg-elevated/30 p-4">
      <LoadingSkeleton v-if="proposalsQuery.isLoading.value" :rows="6" />
      <div v-else-if="items.length" class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="text-muted">
            <tr>
              <th class="pb-2 font-medium">Created</th>
              <th class="pb-2 font-medium">Symbol</th>
              <th class="pb-2 font-medium">Source</th>
              <th class="pb-2 font-medium">Side</th>
              <th class="pb-2 font-medium">Type</th>
              <th class="pb-2 text-right font-medium">Qty</th>
              <th class="pb-2 text-right font-medium">Entry</th>
              <th class="pb-2 text-right font-medium">Stop</th>
              <th class="pb-2 text-right font-medium">Target</th>
              <th class="pb-2 text-right font-medium">Conf.</th>
              <th class="pb-2 text-right font-medium">Expires</th>
              <th class="pb-2 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="proposal in items" :key="proposal.id" class="border-t border-default hover:bg-elevated/40">
              <td class="py-2 text-muted">
                <NuxtLink :to="`/agent/proposals/${proposal.id}`" class="hover:underline">
                  {{ formatDateTime(proposal.created_at) }}
                </NuxtLink>
              </td>
              <td class="py-2"><SymbolBadge :symbol="proposal.symbol" size="sm" /></td>
              <td class="py-2"><StatusBadge :label="proposal.source" :tone="sourceTone[proposal.source] ?? 'neutral'" /></td>
              <td class="py-2">
                <StatusBadge :label="proposal.action" :tone="proposal.action === 'BUY' ? 'success' : proposal.action === 'SELL' ? 'danger' : 'neutral'" />
              </td>
              <td class="py-2 text-muted">{{ proposal.order_type.replace('_', ' ') }}</td>
              <td class="num py-2 text-right text-default">{{ proposal.proposed_quantity }}</td>
              <td class="py-2 text-right"><PriceValue :value="proposal.entry_price" /></td>
              <td class="py-2 text-right"><PriceValue :value="proposal.stop_loss" /></td>
              <td class="py-2 text-right"><PriceValue :value="proposal.take_profit" /></td>
              <td class="py-2 text-right"><PercentageValue :value="proposal.confidence" /></td>
              <td class="py-2 text-right text-muted">{{ formatDateTime(proposal.expires_at) }}</td>
              <td class="py-2 text-right"><ProposalStatusBadge :status="proposal.status" /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState
        v-else
        title="No proposals"
        message="Create a manual proposal or start one from a strategy signal."
        icon="i-lucide-file-text"
      />

      <div v-if="pageCount > 1" class="mt-3 flex items-center justify-between text-xs text-muted">
        <span>Page {{ page }} of {{ pageCount }}</span>
        <div class="flex gap-1">
          <UButton color="neutral" variant="outline" size="xs" :disabled="page <= 1" @click="page -= 1">Prev</UButton>
          <UButton color="neutral" variant="outline" size="xs" :disabled="page >= pageCount" @click="page += 1">Next</UButton>
        </div>
      </div>
    </div>
  </div>
</template>
