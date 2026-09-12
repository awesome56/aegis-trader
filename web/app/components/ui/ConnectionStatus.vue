<script setup lang="ts">
import { useWebSocket } from '~/composables/useWebSocket'

const { status, lastConnectedAt, attempts } = useWebSocket()

const meta = computed(() => {
  switch (status.value) {
    case 'connected':
      return { label: 'Live', tone: 'success' as const, dot: true }
    case 'connecting':
      return { label: 'Connecting', tone: 'warning' as const, dot: true }
    case 'reconnecting':
      return { label: `Reconnecting${attempts.value ? ` (${attempts.value})` : ''}`, tone: 'warning' as const, dot: true }
    default:
      return { label: 'Offline', tone: 'danger' as const, dot: false }
  }
})

const title = computed(() =>
  lastConnectedAt.value ? `Last connected ${lastConnectedAt.value}` : 'Not connected',
)
</script>

<template>
  <span :title="title">
    <StatusBadge
      label="WS"
      :tone="meta.tone"
      :dot="meta.dot"
      :icon="status === 'connected' ? 'i-lucide-radio' : 'i-lucide-wifi-off'"
    />
    <span class="sr-only" role="status">WebSocket {{ meta.label }}</span>
  </span>
</template>
