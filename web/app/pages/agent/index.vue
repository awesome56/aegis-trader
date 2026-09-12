<script setup lang="ts">
import { useAgentStatus } from '~/composables/useAgent'
import { useWebSocket } from '~/composables/useWebSocket'

useHead({ title: 'Agent' })

const { data, isLoading, isError, refetch } = useAgentStatus()
const { recentEvents, isConnected } = useWebSocket()

const recent = computed(() => recentEvents.value.slice(0, 12))
</script>

<template>
  <div>
    <PageHeader title="Agent" subtitle="AI analysis, decisions and proposals." eyebrow="Intelligence">
      <template #actions>
        <ConnectionStatus />
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="isLoading" @click="refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState v-if="isError" title="Agent status unavailable" message="GET /agent/status is not implemented yet." @retry="refetch()" />

    <template v-else>
      <section class="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <MetricCard label="Decisions Today" :value="String(data?.decisions_today ?? 0)" :loading="isLoading" />
        <MetricCard label="Proposals Today" :value="String(data?.proposals_today ?? 0)" :loading="isLoading" />
        <MetricCard label="Approved" :value="String(data?.approved_today ?? 0)" :loading="isLoading" />
        <MetricCard label="Rejected" :value="String(data?.rejected_today ?? 0)" :loading="isLoading" />
      </section>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div class="rounded-lg border border-default bg-elevated/20 p-3">
          <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
            Live activity
          </h2>
          <p v-if="!isConnected" class="text-xs text-muted">
            Waiting for WebSocket connection…
          </p>
          <ul v-else-if="recent.length" class="space-y-1.5">
            <li v-for="(event, index) in recent" :key="index" class="flex gap-2 text-xs">
              <span class="num shrink-0 text-dimmed">{{ event.timestamp.slice(11, 19) }}</span>
              <span class="text-muted">{{ event.event }}</span>
            </li>
          </ul>
          <p v-else class="text-xs text-muted">No live events received yet.</p>
        </div>
        <FeaturePlaceholder title="Decision records" phase="Phase 5" icon="i-lucide-bot" description="Structured decisions with confidence, regime, supporting signals and risk verdict. Concise summaries only — never hidden chain-of-thought." />
      </section>

      <div class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <FeaturePlaceholder title="Trade proposals" phase="Phase 5" icon="i-lucide-file-text" description="Proposals with entry, stop, target, R/R and risk status." />
        <FeaturePlaceholder title="Decision pipeline" phase="Phase 5" icon="i-lucide-git-branch" description="Signals → decision → proposal → risk → order → execution." />
      </div>
    </template>
  </div>
</template>
