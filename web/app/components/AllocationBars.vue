<script setup lang="ts">
import type { AllocationBreakdown, AllocationSlice } from '~/types/portfolio'
import { formatCurrency } from '~/utils/currency'

const props = withDefaults(
  defineProps<{
    breakdown: AllocationBreakdown | null
    loading?: boolean
    currency?: string
  }>(),
  { loading: false, currency: 'USD' },
)

type Dimension = 'by_asset' | 'by_sector' | 'by_asset_class'
const dimension = ref<Dimension>('by_asset')
const tabs: { key: Dimension; label: string }[] = [
  { key: 'by_asset', label: 'Asset' },
  { key: 'by_sector', label: 'Sector' },
  { key: 'by_asset_class', label: 'Class' },
]

const slices = computed<AllocationSlice[]>(() => props.breakdown?.[dimension.value] ?? [])
const maxWeight = computed(() =>
  slices.value.reduce((max, slice) => Math.max(max, Number(slice.weight_pct) || 0), 0) || 1,
)
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-semibold text-highlighted">Allocation</h2>
      <div class="flex gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="rounded px-2 py-0.5 text-[11px] font-medium transition-colors"
          :class="dimension === tab.key ? 'bg-elevated text-highlighted' : 'text-muted hover:text-default'"
          @click="dimension = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>
    <LoadingSkeleton v-if="loading" class="mt-4" :rows="4" />
    <ul v-else-if="slices.length" class="mt-3 space-y-2.5">
      <li v-for="slice in slices" :key="slice.label">
        <div class="flex items-center justify-between text-xs">
          <span class="truncate text-default">{{ slice.label }}</span>
          <span class="num text-muted">
            {{ formatCurrency(slice.value, { currency }) }}
            <span class="ml-1">{{ Number(slice.weight_pct).toFixed(1) }}%</span>
          </span>
        </div>
        <div class="mt-1 h-1.5 overflow-hidden rounded bg-elevated">
          <div
            class="h-full rounded bg-accented"
            :style="{ width: `${Math.min(100, (Number(slice.weight_pct) / maxWeight) * 100)}%` }"
          />
        </div>
      </li>
    </ul>
    <EmptyState v-else title="No allocation data" icon="i-lucide-pie-chart" />
  </div>
</template>
