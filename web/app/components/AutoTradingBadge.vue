<script setup lang="ts">
import { useAutoTradingStatus } from '~/composables/useAutoTrading'

const { data } = useAutoTradingStatus()
const demo = computed(() => data.value?.demo_any_enabled ?? false)
const live = computed(() => data.value?.live_any_enabled ?? false)
</script>

<template>
  <template v-if="demo || live">
    <StatusBadge v-if="live" label="LIVE AUTO TRADING" tone="danger" dot />
    <StatusBadge v-else-if="demo" label="DEMO AUTO TRADING" tone="info" dot />
  </template>
</template>
