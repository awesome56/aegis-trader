<script setup lang="ts">
useHead({ title: 'Trade proposals' })
</script>

<template>
  <div>
    <PageHeader title="Trade Proposals" subtitle="Every proposal and its deterministic risk verdict." eyebrow="Agent" />
    <FeaturePlaceholder
      title="Proposals"
      phase="Phase 5"
      icon="i-lucide-file-text"
      description="Symbol, action, strategy, confidence, proposed position, entry, stop, take profit, risk/reward, risk status, proposal status and creation time."
    />
  </div>
</template>
