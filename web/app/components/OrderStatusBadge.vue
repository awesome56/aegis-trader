<script setup lang="ts">
import type { OrderStatus } from '~/types/order'

const props = defineProps<{ status: OrderStatus }>()

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

const TONES: Record<OrderStatus, Tone> = {
  CREATED: 'neutral',
  VALIDATED: 'info',
  SUBMITTED: 'info',
  ACCEPTED: 'info',
  PARTIALLY_FILLED: 'warning',
  FILLED: 'success',
  CANCELLED: 'neutral',
  REJECTED: 'danger',
  FAILED: 'danger',
}

const label = computed(() => props.status.replaceAll('_', ' '))
</script>

<template>
  <StatusBadge :label="label" :tone="TONES[status]" dot />
</template>
