<script setup lang="ts">
const route = useRoute()
const symbol = computed(() => String(route.params.symbol ?? '').toUpperCase())
useHead({ title: () => symbol.value })
</script>

<template>
  <div>
    <PageHeader
      :title="symbol"
      subtitle="Candlestick chart, indicators, signals and AI summary."
      eyebrow="Asset"
    />
    <FeaturePlaceholder
      title="Asset detail"
      phase="Phase 4"
      icon="i-lucide-candlestick-chart"
      description="Candles + volume, SMA/EMA/Bollinger overlays, RSI/MACD/ATR, market regime, strategy signals, AI analysis summary, current position and recent trades/proposals. All strategy decisions remain backend-authoritative."
    />
  </div>
</template>
