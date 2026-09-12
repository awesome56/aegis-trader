<script setup lang="ts">
useHead({ title: 'Trades' })
</script>

<template>
  <div>
    <PageHeader title="Trades" subtitle="Completed and open trades with performance." eyebrow="Trading" />
    <FeaturePlaceholder
      title="Trade history"
      phase="Phase 7"
      icon="i-lucide-arrow-left-right"
      description="Columns: time, symbol, side, quantity, entry, exit, P&L, return %, strategy, agent confidence, duration, status. Filters: date, symbol, side, strategy, status, profit/loss."
    />
  </div>
</template>
