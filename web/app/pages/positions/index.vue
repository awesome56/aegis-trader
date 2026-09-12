<script setup lang="ts">
useHead({ title: 'Positions' })
</script>

<template>
  <div>
    <PageHeader title="Positions" subtitle="Open exposure with live P&L, weights and stops." eyebrow="Trading" />
    <FeaturePlaceholder
      title="Positions table"
      phase="Phase 3"
      icon="i-lucide-table"
      description="Sortable, filterable positions table (symbol, quantity, entry, price, value, weight, day change, unrealized P&L, return, stop, take profit, strategy) with column visibility and sticky headers."
    />
  </div>
</template>
