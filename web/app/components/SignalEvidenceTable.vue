<script setup lang="ts">
import type { Numeric } from '~/types/api'

const props = withDefaults(
  defineProps<{
    indicators: Record<string, Numeric> | null
    title?: string
  }>(),
  { title: 'Evidence' },
)

interface Row {
  key: string
  label: string
  value: string
}

function formatValue(value: Numeric | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return String(value)
  if (Number.isInteger(numeric)) return String(numeric)
  return numeric.toFixed(Math.abs(numeric) < 1 ? 4 : 2)
}

const rows = computed<Row[]>(() => {
  const entries = Object.entries(props.indicators ?? {})
  return entries
    .filter(([, value]) => value === null || typeof value !== 'object')
    .map(([key, value]) => ({
      key,
      label: key.replaceAll('_', ' '),
      value: formatValue(value),
    }))
    .sort((a, b) => a.label.localeCompare(b.label))
})

const hasRows = computed(() => rows.value.length > 0)
const rawJson = computed(() => JSON.stringify(props.indicators ?? {}, null, 2))
</script>

<template>
  <div>
    <p class="text-xs font-medium text-muted">{{ title }}</p>
    <table v-if="hasRows" class="mt-2 w-full text-left text-xs">
      <tbody>
        <tr v-for="row in rows" :key="row.key" class="border-t border-default first:border-t-0">
          <td class="py-1.5 capitalize text-muted">{{ row.label }}</td>
          <td class="num py-1.5 text-right text-default">{{ row.value }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="mt-2 text-xs text-muted">No structured evidence returned for this signal.</p>

    <details v-if="indicators" class="mt-2">
      <summary class="cursor-pointer text-[11px] text-muted hover:text-default">Raw evidence</summary>
      <pre class="mt-1 max-h-48 overflow-auto rounded bg-elevated/40 p-2 text-[11px] text-muted">{{ rawJson }}</pre>
    </details>
  </div>
</template>
