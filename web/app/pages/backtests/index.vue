<script setup lang="ts">
useHead({ title: 'Backtests' })
</script>

<template>
  <div>
    <PageHeader title="Backtests" subtitle="Strategy validation on historical data." eyebrow="Research" />
    <EmptyState
      title="Backtesting will become available after Backend Phase 8."
      message="Historical simulation, equity curves, drawdown and performance metrics are not implemented yet. No mock results are shown."
      icon="i-lucide-flask-conical"
    />
    <section class="mt-4 rounded-lg border border-default bg-elevated/20 p-4">
      <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">Planned capabilities</h2>
      <ul class="mt-3 grid grid-cols-1 gap-1.5 text-xs text-muted sm:grid-cols-2">
        <li>Strategy selection</li>
        <li>Symbol selection</li>
        <li>Date range</li>
        <li>Timeframe</li>
        <li>Equity curve</li>
        <li>Drawdown</li>
        <li>Performance metrics</li>
        <li>Trade history</li>
      </ul>
    </section>
  </div>
</template>
