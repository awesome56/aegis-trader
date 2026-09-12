<script setup lang="ts">
import type { Numeric } from '~/types/api'
import { formatPercentage } from '~/utils/percentage'
import { pnlTone } from '~/utils/pnl'

const props = withDefaults(
  defineProps<{
    value: Numeric | null | undefined
    decimals?: number
    showSign?: boolean
    asFraction?: boolean
    colorize?: boolean
  }>(),
  { decimals: 2, showSign: false, asFraction: false, colorize: false },
)

const toneClass = computed(() => {
  if (!props.colorize) return 'text-default'
  const tone = pnlTone(props.value)
  return tone === 'up' ? 'text-up' : tone === 'down' ? 'text-down' : 'text-flat'
})
</script>

<template>
  <span class="num tabular-nums" :class="toneClass">
    {{ formatPercentage(value, { decimals, showSign, asFraction }) }}
  </span>
</template>
