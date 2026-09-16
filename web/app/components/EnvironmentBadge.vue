<script setup lang="ts">
const props = defineProps<{ environment?: 'DEMO' | 'LIVE' | null }>()
const isLive = computed(() => props.environment === 'LIVE')
</script>

<template>
  <StatusBadge
    v-if="props.environment"
    :label="props.environment"
    :tone="isLive ? 'danger' : 'info'"
    :title="isLive ? 'Live account' : 'Demo account'"
  />
</template>
