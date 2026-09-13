<script setup lang="ts">
import type { ProposalCreateInput } from '~/types/agent'
import { useCreateProposal } from '~/composables/useProposals'

useHead({ title: 'New Proposal' })

const router = useRouter()
const createProposal = useCreateProposal()
const errorMessage = ref<string | null>(null)

async function onSubmit(input: ProposalCreateInput): Promise<void> {
  errorMessage.value = null
  try {
    const proposal = await createProposal.mutateAsync(input)
    await router.push(`/agent/proposals/${proposal.id}`)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to create proposal.'
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="New Proposal"
      subtitle="Create a proposal for deterministic risk evaluation. No order is placed."
      eyebrow="Execution pipeline"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-arrow-left" to="/agent/proposals">
          All proposals
        </UButton>
      </template>
    </PageHeader>

    <div v-if="errorMessage" class="mb-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
      {{ errorMessage }}
    </div>

    <div class="max-w-2xl rounded-lg border border-default bg-elevated/30 p-4">
      <ProposalForm :submitting="createProposal.isPending.value" @submit="onSubmit" />
    </div>
  </div>
</template>
