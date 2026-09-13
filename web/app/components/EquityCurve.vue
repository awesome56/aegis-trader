<script setup lang="ts">
import type { PortfolioSnapshot } from '~/types/portfolio'
import { formatSignedPercentage } from '~/utils/percentage'

const props = withDefaults(
  defineProps<{
    points: PortfolioSnapshot[]
    loading?: boolean
    benchmark?: boolean
  }>(),
  { loading: false, benchmark: false },
)

const WIDTH = 100
const HEIGHT = 34

function pathFor(values: number[]): string {
  if (values.length < 2) return ''
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * WIDTH
      const y = HEIGHT - ((value - min) / span) * (HEIGHT - 3) - 1.5
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
}

const equity = computed(() =>
  props.points.map((point) => Number(point.equity)).filter((value) => Number.isFinite(value)),
)

const benchmarkValues = computed(() =>
  props.points
    .map((point) => Number(point.benchmark_equity))
    .filter((value) => Number.isFinite(value)),
)

const equityPath = computed(() => pathFor(equity.value))
const benchmarkPath = computed(() => pathFor(benchmarkValues.value))
const areaPath = computed(() =>
  equityPath.value ? `${equityPath.value} L${WIDTH},${HEIGHT} L0,${HEIGHT} Z` : '',
)

const change = computed(() => {
  const values = equity.value
  if (values.length < 2) return null
  const first = values[0]
  const last = values[values.length - 1]
  if (first === undefined || last === undefined || !first) return null
  return ((last - first) / first) * 100
})
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-semibold text-highlighted">Equity curve</h2>
      <span v-if="change !== null" class="num text-xs font-medium" :class="change < 0 ? 'text-down' : 'text-up'">
        {{ formatSignedPercentage(change) }}
      </span>
    </div>
    <LoadingSkeleton v-if="loading" class="mt-4" :rows="4" height="h-10" />
    <div v-else-if="equityPath" class="mt-3">
      <svg
        :viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
        preserveAspectRatio="none"
        class="h-40 w-full text-accented"
        role="img"
        aria-label="Equity curve"
      >
        <path :d="areaPath" fill="currentColor" opacity="0.08" />
        <path v-if="benchmark && benchmarkPath" :d="benchmarkPath" fill="none" stroke="currentColor" stroke-width="0.4" stroke-dasharray="1.5 1.5" opacity="0.5" />
        <path :d="equityPath" fill="none" stroke="currentColor" stroke-width="0.6" />
      </svg>
    </div>
    <EmptyState
      v-else
      class="mt-3"
      title="No equity history yet"
      message="Snapshots accumulate while the worker runs."
      icon="i-lucide-chart-line"
    />
  </div>
</template>
