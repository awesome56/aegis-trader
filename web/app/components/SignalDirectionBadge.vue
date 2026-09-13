<script setup lang="ts">
import type { SignalDirection } from '~/types/market'

const props = defineProps<{ direction: SignalDirection }>()

type Tone = 'success' | 'danger' | 'neutral'
const TONES: Record<SignalDirection, Tone> = {
  LONG: 'success',
  SHORT: 'danger',
  NEUTRAL: 'neutral',
}
</script>

<template>
  <StatusBadge :label="direction" :tone="TONES[props.direction]" />
</template>
