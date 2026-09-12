<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    description?: string
    phase: string
    icon?: string
  }>(),
  { description: undefined, icon: 'i-lucide-hammer' },
)
</script>

<template>
  <div class="rounded-lg border border-default bg-elevated/20 p-4">
    <div class="flex items-start gap-3">
      <UIcon :name="icon" class="mt-0.5 h-5 w-5 shrink-0 text-muted" aria-hidden="true" />
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="text-sm font-semibold text-highlighted">{{ title }}</h2>
          <StatusBadge :label="phase" tone="neutral" />
        </div>
        <p v-if="description" class="mt-1 text-xs text-muted">{{ description }}</p>
        <slot />
      </div>
    </div>
  </div>
</template>
