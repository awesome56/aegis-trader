import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { activityService } from '~/services/api/activity'
import type { PageParams, Paginated } from '~/types/api'
import type { ActivityEvent } from '~/types/activity'

export function useActivity(params: MaybeRefOrGetter<PageParams> = {}) {
  return useQuery<Paginated<ActivityEvent>>({
    queryKey: computed(() => queryKeys.activity(toValue(params))),
    queryFn: () => activityService.list(toValue(params)),
    staleTime: 15_000,
  })
}
