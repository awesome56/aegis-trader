<script setup lang="ts">
import type { Numeric } from '~/types/api'
import { formatCurrency } from '~/utils/currency'

withDefaults(
  defineProps<{
    value: Numeric | null | undefined
    currency?: string
    decimals?: number
    compact?: boolean
    showSign?: boolean
    muted?: boolean
  }>(),
  { currency: 'USD', decimals: 2, compact: false, showSign: false, muted: false },
)
</script>

<template>
  <span class="num tabular-nums" :class="muted ? 'text-muted' : 'text-highlighted'">
    {{ formatCurrency(value, { currency, decimals, compact, showSign }) }}
  </span>
</template>
