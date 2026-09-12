<script setup lang="ts">
useHead({ title: 'Orders' })
</script>

<template>
  <div>
    <PageHeader title="Orders" subtitle="Order lifecycle — read-only from the browser." eyebrow="Trading" />
    <FeaturePlaceholder
      title="Orders workspace"
      phase="Phase 7"
      icon="i-lucide-clipboard-list"
      description="Tabs: Open, Filled, Cancelled, Rejected, All. Columns: order ID, symbol, side, type, quantity, filled, price, status, created, updated, broker ID. The frontend never submits or cancels orders directly."
    />
  </div>
</template>
