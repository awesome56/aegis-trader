<script setup lang="ts">
withDefaults(
  defineProps<{
    symbol: string
    name?: string | null
    size?: 'sm' | 'md'
  }>(),
  { name: null, size: 'md' },
)
</script>

<template>
  <span class="inline-flex items-baseline gap-1.5">
    <span
      class="num font-semibold uppercase tracking-wide text-highlighted"
      :class="size === 'sm' ? 'text-xs' : 'text-sm'"
    >
      {{ symbol }}
    </span>
    <span v-if="name" class="truncate text-xs text-muted">{{ name }}</span>
  </span>
</template>
