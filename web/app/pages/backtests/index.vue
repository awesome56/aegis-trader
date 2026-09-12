<script setup lang="ts">
useHead({ title: 'Backtests' })
</script>

<template>
  <div>
    <PageHeader title="Backtests" subtitle="Strategy validation on historical data." eyebrow="Research" />
    <FeaturePlaceholder
      title="Backtest configuration"
      phase="Phase 9"
      icon="i-lucide-flask-conical"
      description="Strategy, symbols, initial capital, start/end date, timeframe, fees and slippage. Configuration is submitted to the backend — all computation is server-side."
    />
    <div class="mt-4">
      <FeaturePlaceholder
        title="Results"
        phase="Phase 9"
        icon="i-lucide-bar-chart-3"
        description="Return, benchmark, drawdown, Sharpe, Sortino, win rate, profit factor, expectancy, fees, slippage, equity curve, monthly returns and trade history. Past performance does not guarantee future results."
      />
    </div>
  </div>
</template>
