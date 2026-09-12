import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { ordersService } from '~/services/api/orders'
import type { PageParams, Paginated } from '~/types/api'
import type { Order, OrderDetail } from '~/types/order'

export function useOrders(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<Order>>({
    queryKey: computed(() => queryKeys.orders(toValue(params))),
    queryFn: () => ordersService.list(toValue(params)),
    staleTime: 10_000,
  })
}

export function useOrder(id: MaybeRefOrGetter<string>) {
  return useQuery<OrderDetail>({
    queryKey: computed(() => queryKeys.order(toValue(id))),
    queryFn: () => ordersService.get(toValue(id)),
    enabled: computed(() => Boolean(toValue(id))),
  })
}
