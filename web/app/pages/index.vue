<script setup lang="ts">
// Root redirects to the dashboard (auth middleware guards it).
await navigateTo('/dashboard', { replace: true })
</script>

<template>
  <div />
</template>
