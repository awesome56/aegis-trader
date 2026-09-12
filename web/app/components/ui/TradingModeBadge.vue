<script setup lang="ts">
import { useTradingMode } from '~/composables/useSystemStatus'

/**
 * Persistent paper/live indicator. Paper and live must never be confusable:
 * distinct label, color and icon, and the kill-switch state is reflected.
 */
const { mode, isPaper, isEmergencyStopped, killSwitchState } = useTradingMode()

const label = computed(() => (isPaper.value ? 'Paper Trading' : 'Live Trading'))
const tone = computed(() => (isPaper.value ? 'paper' : 'live'))
</script>

<template>
  <div class="flex items-center gap-2">
    <StatusBadge
      :label="label"
      :tone="tone"
      dot
      :icon="isPaper ? 'i-lucide-flask-conical' : 'i-lucide-zap'"
    />
    <StatusBadge
      v-if="isEmergencyStopped"
      label="Emergency Stop"
      tone="danger"
      dot
      icon="i-lucide-octagon-alert"
    />
    <span v-else-if="killSwitchState !== 'TRADING_ENABLED'" class="hidden xl:inline-flex">
      <StatusBadge :label="killSwitchState.replace('TRADING_', '')" tone="warning" dot />
    </span>
    <span class="sr-only" role="status">Trading mode: {{ mode }}</span>
  </div>
</template>
