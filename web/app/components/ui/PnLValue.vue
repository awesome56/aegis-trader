<script setup lang="ts">
import type { Numeric } from '~/types/api'
import { formatPnL, pnlSign, pnlTone } from '~/utils/pnl'

const props = withDefaults(
  defineProps<{
    value: Numeric | null | undefined
    currency?: string
    size?: 'sm' | 'md' | 'lg'
    showArrow?: boolean
  }>(),
  { currency: 'USD', size: 'md', showArrow: true },
)

const tone = computed(() => pnlTone(props.value))
const sign = computed(() => pnlSign(props.value))
const formatted = computed(() => formatPnL(props.value, props.currency))

const toneClass = computed(() =>
  tone.value === 'up' ? 'text-up' : tone.value === 'down' ? 'text-down' : 'text-flat',
)

const sizeClass = computed(
  () => ({ sm: 'text-xs', md: 'text-sm', lg: 'text-base' })[props.size],
)
</script>

<template>
  <span
    class="num inline-flex items-center gap-1 font-medium"
    :class="[toneClass, sizeClass]"
    :aria-label="`${sign}${formatted}`"
  >
    <span v-if="showArrow && tone !== 'flat'" aria-hidden="true">
      {{ tone === 'up' ? '▲' : '▼' }}
    </span>
    <span>{{ formatted }}</span>
  </span>
</template>
