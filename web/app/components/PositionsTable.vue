<script setup lang="ts">
import type { Position } from '~/types/position'
import { formatCurrency } from '~/utils/currency'

const props = withDefaults(
  defineProps<{
    positions: Position[]
    loading?: boolean
    currency?: string
    showStops?: boolean
    showStrategy?: boolean
  }>(),
  { loading: false, currency: 'USD', showStops: false, showStrategy: false },
)

type SortKey =
  | 'symbol'
  | 'quantity'
  | 'average_entry_price'
  | 'current_price'
  | 'market_value'
  | 'weight_pct'
  | 'day_change_pct'
  | 'unrealized_pnl'
  | 'return_pct'

const sortKey = ref<SortKey>('market_value')
const sortDir = ref<'asc' | 'desc'>('desc')

function toggle(key: SortKey): void {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
    return
  }
  sortKey.value = key
  sortDir.value = 'desc'
}

const sorted = computed(() => {
  const rows = [...props.positions]
  const direction = sortDir.value === 'asc' ? 1 : -1
  return rows.sort((a, b) => {
    const left = a[sortKey.value]
    const right = b[sortKey.value]
    if (typeof left === 'string' || typeof right === 'string') {
      return String(left).localeCompare(String(right)) * direction
    }
    return (Number(left) - Number(right)) * direction
  })
})

function indicator(key: SortKey): string {
  if (sortKey.value !== key) return ''
  return sortDir.value === 'asc' ? '▲' : '▼'
}
</script>

<template>
  <div>
    <LoadingSkeleton v-if="loading" :rows="5" />
    <div v-else-if="positions.length" class="overflow-x-auto">
      <table class="w-full text-left text-xs">
        <thead class="text-muted">
          <tr>
            <th class="cursor-pointer pb-2 font-medium" @click="toggle('symbol')">
              Symbol {{ indicator('symbol') }}
            </th>
            <th class="cursor-pointer pb-2 text-right font-medium" @click="toggle('quantity')">
              Qty {{ indicator('quantity') }}
            </th>
            <th class="cursor-pointer pb-2 text-right font-medium" @click="toggle('average_entry_price')">
              Entry {{ indicator('average_entry_price') }}
            </th>
            <th class="cursor-pointer pb-2 text-right font-medium" @click="toggle('current_price')">
              Price {{ indicator('current_price') }}
            </th>
            <th class="cursor-pointer pb-2 text-right font-medium" @click="toggle('market_value')">
              Value {{ indicator('market_value') }}
            </th>
            <th class="cursor-pointer pb-2 text-right font-medium" @click="toggle('weight_pct')">
              Weight {{ indicator('weight_pct') }}
            </th>
            <th class="cursor-pointer pb-2 text-right font-medium" @click="toggle('day_change_pct')">
              Day {{ indicator('day_change_pct') }}
            </th>
            <th class="cursor-pointer pb-2 text-right font-medium" @click="toggle('unrealized_pnl')">
              Unrealized P&L {{ indicator('unrealized_pnl') }}
            </th>
            <th class="cursor-pointer pb-2 text-right font-medium" @click="toggle('return_pct')">
              Return {{ indicator('return_pct') }}
            </th>
            <th v-if="showStops" class="pb-2 text-right font-medium">Stop / Target</th>
            <th v-if="showStrategy" class="pb-2 font-medium">Strategy</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="position in sorted"
            :key="position.id"
            class="border-t border-default hover:bg-elevated/40"
          >
            <td class="py-2">
              <NuxtLink :to="`/positions/${position.id}`" class="hover:underline">
                <SymbolBadge :symbol="position.symbol" :name="position.asset_name" size="sm" />
              </NuxtLink>
            </td>
            <td class="num py-2 text-right text-default">{{ position.quantity }}</td>
            <td class="py-2 text-right"><PriceValue :value="position.average_entry_price" /></td>
            <td class="py-2 text-right"><PriceValue :value="position.current_price" /></td>
            <td class="num py-2 text-right text-default">
              {{ formatCurrency(position.market_value, { currency }) }}
            </td>
            <td class="py-2 text-right"><PercentageValue :value="position.weight_pct" /></td>
            <td class="py-2 text-right">
              <PercentageValue v-if="position.day_change_pct !== null" :value="position.day_change_pct" show-sign colorize />
              <span v-else class="text-muted">—</span>
            </td>
            <td class="py-2 text-right">
              <PnLValue :value="position.unrealized_pnl" :currency="currency" size="sm" />
            </td>
            <td class="py-2 text-right">
              <PercentageValue :value="position.return_pct" show-sign colorize />
            </td>
            <td v-if="showStops" class="py-2 text-right">
              <span class="num text-muted">
                {{ position.stop_loss ? formatCurrency(position.stop_loss, { currency }) : '—' }}
                /
                {{ position.take_profit ? formatCurrency(position.take_profit, { currency }) : '—' }}
              </span>
            </td>
            <td v-if="showStrategy" class="py-2 text-muted">{{ position.strategy_name ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <EmptyState
      v-else
      title="No open positions"
      message="Positions appear here once an approved proposal is executed."
      icon="i-lucide-briefcase"
    />
  </div>
</template>
