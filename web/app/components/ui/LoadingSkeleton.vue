<script setup lang="ts">
withDefaults(
  defineProps<{
    rows?: number
    height?: string
  }>(),
  { rows: 3, height: 'h-4' },
)
</script>

<template>
  <div class="space-y-3" role="status" aria-busy="true" aria-label="Loading">
    <div
      v-for="row in rows"
      :key="row"
      class="animate-pulse rounded bg-elevated"
      :class="[height, row % 3 === 0 ? 'w-2/3' : 'w-full']"
    />
    <span class="sr-only">Loading…</span>
  </div>
</template>
