<script setup lang="ts">
import type { ProposalStatus } from '~/types/agent'

const props = defineProps<{ status: ProposalStatus }>()

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

const TONES: Record<ProposalStatus, Tone> = {
  DRAFT: 'neutral',
  PENDING: 'info',
  PENDING_RISK: 'info',
  RISK_APPROVED: 'success',
  READY_FOR_EXECUTION: 'success',
  APPROVED: 'success',
  EXECUTING: 'info',
  EXECUTED: 'success',
  RISK_REJECTED: 'danger',
  REJECTED: 'danger',
  FAILED: 'danger',
  EXPIRED: 'warning',
  CANCELLED: 'neutral',
}

const label = computed(() => props.status.replaceAll('_', ' '))
</script>

<template>
  <StatusBadge :label="label" :tone="TONES[status]" dot />
</template>
