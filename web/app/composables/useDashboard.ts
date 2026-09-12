import { useQuery } from '@tanstack/vue-query'
import { queryKeys } from '~/services/api/keys'
import { dashboardService } from '~/services/api/dashboard'
import type { DashboardData } from '~/types/dashboard'

export function useDashboard() {
  return useQuery<DashboardData>({
    queryKey: queryKeys.dashboard,
    queryFn: () => dashboardService.get(),
    staleTime: 10_000,
  })
}
