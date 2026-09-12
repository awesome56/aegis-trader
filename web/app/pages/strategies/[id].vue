<script setup lang="ts">
const route = useRoute()
const strategyId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Strategy ${strategyId.value}` })
</script>

<template>
  <div>
    <PageHeader :title="`Strategy ${strategyId}`" subtitle="Configuration, performance and signals." eyebrow="Strategy" />
    <FeaturePlaceholder
      title="Strategy detail"
      phase="Phase 8"
      icon="i-lucide-workflow"
      description="Description, configuration parameters, current status, historical performance and equity curve, recent signals and trades, backtest results, and assets currently generating signals."
    />
  </div>
</template>
