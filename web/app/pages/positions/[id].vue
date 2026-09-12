<script setup lang="ts">
const route = useRoute()
const positionId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Position ${positionId.value}` })
</script>

<template>
  <div>
    <PageHeader
      :title="`Position ${positionId}`"
      subtitle="Trading workspace — chart, position detail and audit chain."
      eyebrow="Position"
    />
    <FeaturePlaceholder
      title="Position workspace"
      phase="Phase 3"
      icon="i-lucide-candlestick-chart"
      description="Candlestick chart with timeframe selector plus a detail panel: price movement, quantity, average entry, value, unrealized/realized P&L, weight, entry date, stops, strategy, associated decision/proposal/orders/executions."
    />
  </div>
</template>
