<script setup lang="ts">
withDefaults(
  defineProps<{
    message?: string
    title?: string
  }>(),
  { message: 'Something went wrong.', title: 'Error' },
)

defineEmits<{ retry: [] }>()
</script>

<template>
  <div
    class="flex flex-col items-center justify-center rounded-lg border border-danger/30 bg-danger/5 px-6 py-8 text-center"
    role="alert"
  >
    <UIcon name="i-lucide-triangle-alert" class="mb-3 h-7 w-7 text-danger" aria-hidden="true" />
    <p class="text-sm font-medium text-highlighted">{{ title }}</p>
    <p class="mt-1 max-w-md text-xs text-muted">{{ message }}</p>
    <UButton
      class="mt-4"
      color="neutral"
      variant="outline"
      size="sm"
      icon="i-lucide-refresh-cw"
      @click="$emit('retry')"
    >
      Retry
    </UButton>
  </div>
</template>
