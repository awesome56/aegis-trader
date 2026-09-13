<script setup lang="ts">
import type { Candle } from '~/types/market'

const props = withDefaults(
  defineProps<{
    candles: Candle[]
    loading?: boolean
  }>(),
  { loading: false },
)

const WIDTH = 100
const HEIGHT = 40

const closes = computed(() =>
  props.candles.map((candle) => Number(candle.close)).filter((value) => Number.isFinite(value)),
)

const path = computed(() => {
  const values = closes.value
  if (values.length < 2) return ''
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * WIDTH
      const y = HEIGHT - ((value - min) / span) * (HEIGHT - 4) - 2
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
})

const area = computed(() => (path.value ? `${path.value} L${WIDTH},${HEIGHT} L0,${HEIGHT} Z` : ''))
</script>

<template>
  <div>
    <LoadingSkeleton v-if="loading" :rows="5" height="h-12" />
    <div v-else-if="path" class="overflow-x-auto">
      <svg :viewBox="`0 0 ${WIDTH} ${HEIGHT}`" preserveAspectRatio="none" class="h-56 w-full text-accented" role="img" aria-label="Price chart">
        <path :d="area" fill="currentColor" opacity="0.08" />
        <path :d="path" fill="none" stroke="currentColor" stroke-width="0.5" />
      </svg>
    </div>
    <EmptyState v-else title="No candles" message="No price history is available for this timeframe." icon="i-lucide-candlestick-chart" />
  </div>
</template>
