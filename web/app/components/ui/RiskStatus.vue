<script setup lang="ts">
import type { RiskLevel } from '~/types/risk'

const props = withDefaults(
  defineProps<{
    level: RiskLevel
    label?: string
  }>(),
  { label: undefined },
)

const tone = computed(() => {
  switch (props.level) {
    case 'SAFE':
      return 'success' as const
    case 'WARNING':
      return 'warning' as const
    default:
      return 'danger' as const
  }
})

const icon = computed(() => {
  switch (props.level) {
    case 'SAFE':
      return 'i-lucide-shield-check'
    case 'WARNING':
      return 'i-lucide-shield-alert'
    default:
      return 'i-lucide-shield-x'
  }
})
</script>

<template>
  <StatusBadge :label="label ?? level" :tone="tone" dot :icon="icon" />
</template>
