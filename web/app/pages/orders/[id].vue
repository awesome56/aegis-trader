<script setup lang="ts">
import { useCancelOrder, useOrder } from '~/composables/useOrders'
import { useProposalDetail } from '~/composables/useProposals'
import { formatCurrency } from '~/utils/currency'
import { formatDateTime } from '~/utils/dates'
import { isOrderCancellable } from '~/utils/order'

const route = useRoute()
const orderId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Order ${orderId.value}` })

const orderQuery = useOrder(orderId)
const cancelOrder = useCancelOrder()

const order = computed(() => orderQuery.data.value ?? null)
const proposalId = computed(() => order.value?.proposal_id ?? '')
const proposalQuery = useProposalDetail(proposalId)

const executions = computed(() => {
  const detail = proposalQuery.data.value
  if (!detail || !order.value) return []
  return detail.executions.filter((execution) => execution.order_id === order.value!.id)
})

const canCancel = computed(() => !!order.value && isOrderCancellable(order.value.status))
const dialog = reactive({ open: false, loading: false })
const actionError = ref<string | null>(null)

function openDialog(): void {
  actionError.value = null
  dialog.open = true
}

async function runCancel(): Promise<void> {
  dialog.loading = true
  actionError.value = null
  try {
    await cancelOrder.mutateAsync(orderId.value)
    dialog.open = false
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : 'Cancellation failed.'
  } finally {
    dialog.loading = false
  }
}

const summary = computed(() => {
  const o = order.value
  if (!o) return []
  return [
    { label: 'Side', value: o.side },
    { label: 'Type', value: o.order_type.replace('_', ' ') },
    { label: 'Time in force', value: o.time_in_force },
    { label: 'Quantity', value: String(o.quantity) },
    { label: 'Filled', value: String(o.filled_quantity) },
    { label: 'Remaining', value: String(o.remaining_quantity) },
    { label: 'Created', value: formatDateTime(o.created_at) },
    { label: 'Submitted', value: formatDateTime(o.submitted_at) },
    { label: 'Filled at', value: formatDateTime(o.filled_at) },
    { label: 'Cancelled at', value: formatDateTime(o.cancelled_at) },
    { label: 'Client order ID', value: o.idempotency_key || '—' },
    { label: 'Broker order ID', value: o.broker_order_id ?? '—' },
  ]
})
</script>

<template>
  <div>
    <PageHeader
      :title="order ? `${order.symbol} order` : `Order ${orderId}`"
      subtitle="Order, broker response and executions."
      eyebrow="Order"
    >
      <template #actions>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-arrow-left" to="/orders">
          All orders
        </UButton>
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-refresh-cw" :loading="orderQuery.isLoading.value" @click="orderQuery.refetch()">
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="orderQuery.isError.value"
      title="Order unavailable"
      message="This order could not be loaded. It may not exist, or the backend is unreachable."
      @retry="orderQuery.refetch()"
    />
    <LoadingSkeleton v-else-if="orderQuery.isLoading.value" :rows="8" />

    <template v-else-if="order">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <OrderStatusBadge :status="order.status" />
        <StatusBadge :label="order.side" :tone="order.side === 'BUY' ? 'success' : 'danger'" />
        <StatusBadge :label="order.order_type.replace('_', ' ')" tone="neutral" />
        <NuxtLink v-if="proposalId" :to="`/agent/proposals/${proposalId}`" class="text-xs text-muted hover:text-highlighted">
          View proposal →
        </NuxtLink>
      </div>

      <div v-if="actionError" class="mb-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
        {{ actionError }}
      </div>

      <div class="flex flex-wrap gap-2">
        <UButton color="warning" variant="outline" size="sm" icon="i-lucide-x" :disabled="!canCancel" @click="openDialog">
          Cancel Order
        </UButton>
        <span v-if="!canCancel" class="self-center text-[11px] text-muted">
          Terminal orders cannot be cancelled.
        </span>
      </div>

      <section class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="rounded-lg border border-default bg-elevated/30 p-4 xl:col-span-2">
          <h2 class="text-sm font-semibold text-highlighted">Order</h2>
          <dl class="mt-3 grid grid-cols-2 gap-y-3 text-xs lg:grid-cols-3">
            <template v-for="row in summary" :key="row.label">
              <dt class="text-muted">{{ row.label }}</dt>
              <dd class="text-right text-default">{{ row.value }}</dd>
            </template>
          </dl>
        </div>

        <div class="rounded-lg border border-default bg-elevated/30 p-4">
          <h2 class="text-sm font-semibold text-highlighted">Pricing</h2>
          <dl class="mt-3 space-y-3 text-xs">
            <div class="flex items-center justify-between">
              <dt class="text-muted">Limit price</dt>
              <dd><PriceValue :value="order.limit_price" /></dd>
            </div>
            <div class="flex items-center justify-between">
              <dt class="text-muted">Stop price</dt>
              <dd><PriceValue :value="order.stop_price" /></dd>
            </div>
            <div class="flex items-center justify-between">
              <dt class="text-muted">Average fill</dt>
              <dd><PriceValue :value="order.average_fill_price" /></dd>
            </div>
            <div class="flex items-center justify-between">
              <dt class="text-muted">Commission</dt>
              <dd class="num text-default">{{ formatCurrency(order.fees, { currency: 'USD' }) }}</dd>
            </div>
          </dl>
          <p v-if="order.error_message" class="mt-3 text-xs text-down">{{ order.error_message }}</p>
        </div>
      </section>

      <section class="mt-4 rounded-lg border border-default bg-elevated/30 p-4">
        <h2 class="text-sm font-semibold text-highlighted">Executions</h2>
        <div v-if="executions.length" class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Execution</th>
                <th class="pb-2 text-right font-medium">Qty</th>
                <th class="pb-2 text-right font-medium">Price</th>
                <th class="pb-2 text-right font-medium">Commission</th>
                <th class="pb-2 text-right font-medium">Liquidity</th>
                <th class="pb-2 text-right font-medium">Executed</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="execution in executions" :key="execution.id" class="border-t border-default">
                <td class="py-2 text-muted"><span class="num">{{ execution.id.slice(0, 8) }}</span></td>
                <td class="num py-2 text-right text-default">{{ execution.quantity }}</td>
                <td class="py-2 text-right"><PriceValue :value="execution.price" /></td>
                <td class="num py-2 text-right text-muted">{{ execution.commission }}</td>
                <td class="py-2 text-right text-muted">{{ execution.liquidity ?? '—' }}</td>
                <td class="py-2 text-right text-muted">{{ formatDateTime(execution.executed_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState
          v-else
          :title="proposalId ? 'No executions linked' : 'Execution detail not available'"
          :message="proposalId
            ? 'This order has no recorded fills yet.'
            : 'Standalone paper orders do not expose execution-level detail through the broker API.'"
          icon="i-lucide-activity"
        />
      </section>
    </template>

    <ConfirmationDialog
      v-model:open="dialog.open"
      title="Cancel order"
      description="Cancel this working paper order. Any filled quantity cannot be undone."
      :consequences="order ? [`${order.symbol} ${order.side} ${order.quantity}`, `Filled ${order.filled_quantity} · remaining ${order.remaining_quantity}`, 'PAPER TRADING environment'] : []"
      tone="danger"
      confirm-label="Cancel order"
      :loading="dialog.loading"
      @confirm="runCancel"
    />
  </div>
</template>
