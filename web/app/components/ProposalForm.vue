<script setup lang="ts">
import type { ProposalCreateInput, TimeHorizon } from '~/types/agent'
import type { OrderSide, OrderType } from '~/types/order'
import { proposalFormErrors } from '~/utils/proposal'

const props = withDefaults(
  defineProps<{
    initial?: Partial<ProposalCreateInput>
    submitting?: boolean
  }>(),
  { initial: () => ({}), submitting: false },
)

const emit = defineEmits<{ submit: [ProposalCreateInput] }>()

const SIDES: OrderSide[] = ['BUY', 'SELL']
const ORDER_TYPES: OrderType[] = ['MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT']
const HORIZONS: TimeHorizon[] = ['INTRADAY', 'SWING', 'POSITION', 'LONG_TERM']

const symbol = ref(props.initial.symbol ?? '')
const side = ref<OrderSide>(props.initial.side ?? 'BUY')
const orderType = ref<OrderType>(props.initial.order_type ?? 'MARKET')
const sizeMode = ref<'quantity' | 'notional'>('quantity')
const quantity = ref(props.initial.quantity ?? '')
const notional = ref(props.initial.notional ?? '')
const limitPrice = ref(props.initial.limit_price ?? '')
const stopPrice = ref(props.initial.stop_price ?? '')
const stopLoss = ref(props.initial.stop_loss ?? '')
const takeProfit = ref(props.initial.take_profit ?? '')
const timeHorizon = ref<TimeHorizon>(props.initial.time_horizon ?? 'SWING')
const confidence = ref(props.initial.confidence ?? '0.6')
const reasoning = ref(props.initial.reasoning_summary ?? '')
const strategySignalId = ref(props.initial.strategy_signal_id ?? '')

const requiresLimit = computed(() => orderType.value === 'LIMIT' || orderType.value === 'STOP_LIMIT')
const requiresStop = computed(() => orderType.value === 'STOP' || orderType.value === 'STOP_LIMIT')

const errors = computed(() =>
  proposalFormErrors({
    symbol: symbol.value,
    sizeMode: sizeMode.value,
    quantity: quantity.value,
    notional: notional.value,
    orderType: orderType.value,
    limitPrice: limitPrice.value,
    stopPrice: stopPrice.value,
    stopLoss: stopLoss.value,
    takeProfit: takeProfit.value,
    confidence: confidence.value,
  }),
)

const canSubmit = computed(() => errors.value.length === 0 && !props.submitting)

function submit(): void {
  if (!canSubmit.value) return
  emit('submit', {
    symbol: symbol.value.trim().toUpperCase(),
    side: side.value,
    order_type: orderType.value,
    quantity: sizeMode.value === 'quantity' ? quantity.value : undefined,
    notional: sizeMode.value === 'notional' ? notional.value : undefined,
    limit_price: requiresLimit.value ? limitPrice.value : undefined,
    stop_price: requiresStop.value ? stopPrice.value : undefined,
    stop_loss: stopLoss.value || undefined,
    take_profit: takeProfit.value || undefined,
    strategy_signal_id: strategySignalId.value || null,
    time_horizon: timeHorizon.value,
    confidence: confidence.value,
    reasoning_summary: reasoning.value || null,
  })
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div>
        <label class="mb-1 block text-xs font-medium text-muted" for="proposal-symbol">Symbol</label>
        <UInput id="proposal-symbol" v-model="symbol" placeholder="AAPL" class="w-full" />
      </div>
      <div>
        <label class="mb-1 block text-xs font-medium text-muted">Side</label>
        <div class="flex gap-1">
          <button
            v-for="option in SIDES"
            :key="option"
            type="button"
            class="flex-1 rounded border px-3 py-1.5 text-xs font-medium transition-colors"
            :class="side === option ? 'border-accented bg-elevated text-highlighted' : 'border-default text-muted hover:text-default'"
            @click="side = option"
          >
            {{ option }}
          </button>
        </div>
      </div>
    </div>

    <div>
      <label class="mb-1 block text-xs font-medium text-muted">Order type</label>
      <div class="flex flex-wrap gap-1">
        <button
          v-for="option in ORDER_TYPES"
          :key="option"
          type="button"
          class="rounded border px-3 py-1.5 text-xs font-medium transition-colors"
          :class="orderType === option ? 'border-accented bg-elevated text-highlighted' : 'border-default text-muted hover:text-default'"
          @click="orderType = option"
        >
          {{ option.replace('_', ' ') }}
        </button>
      </div>
    </div>

    <div>
      <label class="mb-1 block text-xs font-medium text-muted">Size</label>
      <div class="mb-2 flex gap-1">
        <button
          type="button"
          class="rounded border px-3 py-1 text-xs font-medium"
          :class="sizeMode === 'quantity' ? 'border-accented bg-elevated text-highlighted' : 'border-default text-muted'"
          @click="sizeMode = 'quantity'"
        >
          By quantity
        </button>
        <button
          type="button"
          class="rounded border px-3 py-1 text-xs font-medium"
          :class="sizeMode === 'notional' ? 'border-accented bg-elevated text-highlighted' : 'border-default text-muted'"
          @click="sizeMode = 'notional'"
        >
          By notional
        </button>
      </div>
      <UInput v-if="sizeMode === 'quantity'" v-model="quantity" placeholder="10" class="w-full" />
      <UInput v-else v-model="notional" placeholder="1000.00" class="w-full" />
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div v-if="requiresLimit">
        <label class="mb-1 block text-xs font-medium text-muted">Limit price</label>
        <UInput v-model="limitPrice" placeholder="190.00" class="w-full" />
      </div>
      <div v-if="requiresStop">
        <label class="mb-1 block text-xs font-medium text-muted">Stop price</label>
        <UInput v-model="stopPrice" placeholder="185.00" class="w-full" />
      </div>
    </div>

    <div class="rounded-md border border-default bg-elevated/20 p-3">
      <p class="text-[11px] font-medium uppercase tracking-wide text-muted">Risk controls (evaluated deterministically)</p>
      <div class="mt-2 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="mb-1 block text-xs text-muted" for="proposal-stop-loss">Stop loss</label>
          <UInput id="proposal-stop-loss" v-model="stopLoss" placeholder="180.00" class="w-full" />
        </div>
        <div>
          <label class="mb-1 block text-xs text-muted" for="proposal-take-profit">Take profit</label>
          <UInput id="proposal-take-profit" v-model="takeProfit" placeholder="220.00" class="w-full" />
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div>
        <label class="mb-1 block text-xs font-medium text-muted">Time horizon</label>
        <div class="flex flex-wrap gap-1">
          <button
            v-for="option in HORIZONS"
            :key="option"
            type="button"
            class="rounded border px-2.5 py-1 text-[11px] font-medium"
            :class="timeHorizon === option ? 'border-accented bg-elevated text-highlighted' : 'border-default text-muted'"
            @click="timeHorizon = option"
          >
            {{ option.replace('_', ' ') }}
          </button>
        </div>
      </div>
      <div>
        <label class="mb-1 block text-xs font-medium text-muted" for="proposal-confidence">Confidence (0–1)</label>
        <UInput id="proposal-confidence" v-model="confidence" placeholder="0.6" class="w-full" />
      </div>
    </div>

    <div>
      <label class="mb-1 block text-xs font-medium text-muted" for="proposal-reasoning">Reasoning summary (optional)</label>
      <UTextarea id="proposal-reasoning" v-model="reasoning" :rows="2" class="w-full" />
    </div>

    <div v-if="strategySignalId">
      <p class="text-[11px] text-muted">Linked strategy signal: <span class="num">{{ strategySignalId }}</span></p>
    </div>

    <ul v-if="errors.length" class="space-y-1 text-xs text-down">
      <li v-for="error in errors" :key="error">{{ error }}</li>
    </ul>

    <div class="flex items-center justify-between gap-3">
      <p class="text-[11px] text-muted">
        Creating a proposal does not place an order. It must pass the Risk Engine.
      </p>
      <UButton type="submit" color="primary" size="sm" :loading="submitting" :disabled="!canSubmit">
        Create proposal
      </UButton>
    </div>
  </form>
</template>
