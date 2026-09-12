<script setup lang="ts">
const route = useRoute()
const backtestId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Backtest ${backtestId.value}` })
</script>

<template>
  <div>
    <PageHeader :title="`Backtest ${backtestId}`" subtitle="Performance metrics and equity curve." eyebrow="Backtest" />
    <FeaturePlaceholder
      title="Backtest result"
      phase="Phase 9"
      icon="i-lucide-bar-chart-3"
      description="Metrics, equity curve, drawdown, monthly returns, trade distribution and trade history."
    />
  </div>
</template>
