<script setup lang="ts">
const route = useRoute()
const orderId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Order ${orderId.value}` })
</script>

<template>
  <div>
    <PageHeader :title="`Order ${orderId}`" subtitle="Order, broker response and executions." eyebrow="Order" />
    <FeaturePlaceholder
      title="Order detail"
      phase="Phase 7"
      icon="i-lucide-list-tree"
      description="Status timeline, broker identifiers, fill details and executions."
    />
  </div>
</template>
