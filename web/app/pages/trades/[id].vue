<script setup lang="ts">
const route = useRoute()
const tradeId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Trade ${tradeId.value}` })
</script>

<template>
  <div>
    <PageHeader
      :title="`Trade ${tradeId}`"
      subtitle="Why did this trade happen — the full audit chain."
      eyebrow="Trade"
    />
    <FeaturePlaceholder
      title="Trade detail"
      phase="Phase 7"
      icon="i-lucide-receipt"
      description="Summary, execution timeline, entry/exit, fees, slippage, realized P&L, strategy, agent decision, risk evaluation, orders and executions, plus the relevant market chart."
    />
  </div>
</template>
