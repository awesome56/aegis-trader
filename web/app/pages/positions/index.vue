<script setup lang="ts">
import { usePositions } from '~/composables/usePositions'
import { usePortfolio } from '~/composables/usePortfolio'

useHead({ title: 'Positions' })

const positionsQuery = usePositions()
const portfolioQuery = usePortfolio()

const search = ref('')
const currency = computed(() => portfolioQuery.data.value?.currency ?? 'USD')

const positions = computed(() => {
  const items = positionsQuery.data.value?.items ?? []
  const term = search.value.trim().toUpperCase()
  if (!term) return items
  return items.filter(
    (position) =>
      position.symbol.includes(term) ||
      (position.asset_name ?? '').toUpperCase().includes(term),
  )
})
</script>

<template>
  <div>
    <PageHeader
      title="Positions"
      subtitle="Open exposure with live P&L, weights and stops."
      eyebrow="Trading"
    >
      <template #actions>
        <UInput
          v-model="search"
          size="sm"
          placeholder="Filter symbol…"
          icon="i-lucide-search"
          class="w-48"
        />
        <UButton
          color="neutral"
          variant="outline"
          size="sm"
          icon="i-lucide-refresh-cw"
          :loading="positionsQuery.isLoading.value"
          @click="positionsQuery.refetch()"
        >
          Refresh
        </UButton>
      </template>
    </PageHeader>

    <ErrorState
      v-if="positionsQuery.isError.value"
      title="Positions unavailable"
      message="The backend did not return positions. Check the connection and retry."
      @retry="positionsQuery.refetch()"
    />

    <div v-else class="rounded-lg border border-default bg-elevated/30 p-4">
      <PositionsTable
        :positions="positions"
        :loading="positionsQuery.isLoading.value"
        :currency="currency"
        show-stops
        show-strategy
      />
    </div>
  </div>
</template>
