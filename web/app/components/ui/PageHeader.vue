<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
  eyebrow?: string
}>()
</script>

<template>
  <header class="mb-4 flex flex-wrap items-start justify-between gap-3">
    <div class="min-w-0">
      <p v-if="eyebrow" class="text-[11px] font-medium uppercase tracking-wider text-muted">
        {{ eyebrow }}
      </p>
      <h1 class="text-xl font-semibold tracking-tight text-highlighted">{{ title }}</h1>
      <p v-if="subtitle" class="mt-0.5 text-sm text-muted">{{ subtitle }}</p>
    </div>
    <div class="flex shrink-0 items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>
