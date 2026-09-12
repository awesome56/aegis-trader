import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { tradesService } from '~/services/api/trades'
import type { PageParams, Paginated } from '~/types/api'
import type { Trade, TradeDetail } from '~/types/trade'

export function useTrades(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<Trade>>({
    queryKey: computed(() => queryKeys.trades(toValue(params))),
    queryFn: () => tradesService.list(toValue(params)),
    staleTime: 10_000,
  })
}

export function useTrade(id: MaybeRefOrGetter<string>) {
  return useQuery<TradeDetail>({
    queryKey: computed(() => queryKeys.trade(toValue(id))),
    queryFn: () => tradesService.get(toValue(id)),
    enabled: computed(() => Boolean(toValue(id))),
  })
}
