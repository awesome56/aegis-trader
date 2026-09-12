<script setup lang="ts">
useHead({ title: 'Activity' })
</script>

<template>
  <div>
    <PageHeader title="Activity" subtitle="Complete audit trail across the platform." eyebrow="Audit" />
    <FeaturePlaceholder
      title="Audit timeline"
      phase="Phase 10"
      icon="i-lucide-activity"
      description="Agent, Strategy, Risk, Order, Broker, Portfolio and System events with component/event-type/severity/symbol/date filters. Every completed trade traces from market data through to portfolio update."
    />
  </div>
</template>
