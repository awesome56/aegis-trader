<script setup lang="ts">
useHead({ title: 'Risk' })
</script>

<template>
  <div>
    <PageHeader title="Risk" subtitle="Deterministic risk-control centre." eyebrow="Risk engine" />
    <FeaturePlaceholder
      title="Risk control centre"
      phase="Phase 6"
      icon="i-lucide-shield-alert"
      description="Overall risk status, exposure, daily loss, drawdown, open positions and trades today, plus per-limit progress (max position size, exposure, open positions, daily loss, drawdown, trades/day, minimum confidence, minimum R/R, sector and asset-class exposure)."
    />
    <div class="mt-4">
      <FeaturePlaceholder
        title="Trading controls"
        phase="Phase 6"
        icon="i-lucide-power"
        description="Trading enabled/disabled, pause, resume and emergency stop. Dangerous actions require multi-step confirmation."
      />
    </div>
  </div>
</template>
