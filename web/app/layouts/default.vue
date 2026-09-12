<script setup lang="ts">
import { useRealtime } from '~/composables/useRealtime'

// Start the single realtime → cache/notification bridge once.
const { start } = useRealtime()
onMounted(() => start())
</script>

<template>
  <div class="flex min-h-screen flex-col bg-default">
    <AppTopbar />
    <div class="flex min-h-0 flex-1">
      <AppSidebar />
      <main class="min-w-0 flex-1 px-4 py-4 lg:px-6 lg:py-5">
        <slot />
      </main>
    </div>
    <QuickSwitch />
  </div>
</template>
