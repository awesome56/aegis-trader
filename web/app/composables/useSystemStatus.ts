import { useQuery } from '@tanstack/vue-query'
import { queryKeys } from '~/services/api/keys'
import { systemService } from '~/services/api/system'
import type { HealthStatus, KillSwitchState, SystemStatus, TradingMode } from '~/types/system'

/** Backend system status (paper/live mode, kill switch, health). */
export function useSystemStatus() {
  const statusQuery = useQuery<SystemStatus>({
    queryKey: queryKeys.systemStatus,
    queryFn: () => systemService.getStatus(),
    staleTime: 30_000,
  })

  const healthQuery = useQuery<HealthStatus>({
    queryKey: queryKeys.health,
    queryFn: () => systemService.getHealth(),
    staleTime: 20_000,
    retry: 0,
  })

  return { statusQuery, healthQuery }
}

/**
 * Trading mode must always be visually obvious and are never confused between
 * paper and live.
 */
export function useTradingMode() {
  const { statusQuery } = useSystemStatus()

  const mode = computed<TradingMode>(() => statusQuery.data.value?.trading_mode ?? 'paper')
  const isPaper = computed(() => mode.value === 'paper')
  const isLive = computed(() => mode.value === 'live')
  const killSwitchState = computed<KillSwitchState>(
    () => statusQuery.data.value?.kill_switch_state ?? 'TRADING_ENABLED',
  )
  const isEmergencyStopped = computed(() => killSwitchState.value === 'EMERGENCY_STOP')
  const isPaused = computed(() => killSwitchState.value === 'TRADING_PAUSED')
  const isDisabled = computed(() => killSwitchState.value === 'TRADING_DISABLED')
  const isTradingActive = computed(
    () => killSwitchState.value === 'TRADING_ENABLED' && !isEmergencyStopped.value,
  )

  return {
    mode,
    isPaper,
    isLive,
    killSwitchState,
    isEmergencyStopped,
    isPaused,
    isDisabled,
    isTradingActive,
  }
}
