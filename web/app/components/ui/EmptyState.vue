<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    message?: string
    icon?: string
  }>(),
  { message: undefined, icon: 'i-lucide-inbox' },
)
</script>

<template>
  <div
    class="flex flex-col items-center justify-center rounded-lg border border-dashed border-default px-6 py-10 text-center"
  >
    <UIcon :name="icon" class="mb-3 h-8 w-8 text-dimmed" aria-hidden="true" />
    <p class="text-sm font-medium text-highlighted">{{ title }}</p>
    <p v-if="message" class="mt-1 max-w-md text-xs text-muted">{{ message }}</p>
    <div class="mt-4">
      <slot name="action" />
    </div>
  </div>
</template>
