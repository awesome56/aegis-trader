<script setup lang="ts">
import type { Numeric } from '~/types/api'
import { formatPrice } from '~/utils/currency'

withDefaults(
  defineProps<{
    value: Numeric | null | undefined
    decimals?: number
  }>(),
  { decimals: undefined },
)
</script>

<template>
  <span class="num tabular-nums text-default">{{ formatPrice(value, decimals) }}</span>
</template>
