import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { positionsService } from '~/services/api/positions'
import type { PageParams, Paginated } from '~/types/api'
import type { Position, PositionDetail } from '~/types/position'

export function usePositions(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<Position>>({
    queryKey: computed(() => queryKeys.positions(toValue(params))),
    queryFn: () => positionsService.list(toValue(params)),
    staleTime: 10_000,
  })
}

export function usePosition(id: MaybeRefOrGetter<string>) {
  return useQuery<PositionDetail>({
    queryKey: computed(() => queryKeys.position(toValue(id))),
    queryFn: () => positionsService.get(toValue(id)),
    enabled: computed(() => Boolean(toValue(id))),
  })
}
