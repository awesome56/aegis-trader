import type { ISODateString } from './api'

export type TradingMode = 'paper' | 'live'
export type KillSwitchState =
  | 'TRADING_ENABLED'
  | 'TRADING_PAUSED'
  | 'TRADING_DISABLED'
  | 'EMERGENCY_STOP'

export type ComponentStatus = 'healthy' | 'degraded' | 'unhealthy' | 'not_configured'

export interface LiveTradingGuard {
  allowed: boolean
  missing_requirements: string[]
}

/** Matches `GET /system/status`. */
export interface SystemStatus {
  app_name: string
  version: string
  environment: string
  trading_mode: TradingMode
  live_trading_enabled: boolean
  live_trading_guard: LiveTradingGuard
  broker_provider: string
  market_data_provider: string
  agent_enabled: boolean
  kill_switch_state: KillSwitchState
  server_time: ISODateString
}

export interface ComponentHealth {
  name: string
  status: ComponentStatus
  latency_ms: number | null
  detail: string | null
}

/** Matches `GET /health`. */
export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  service: string
  version: string
  environment: string
  timestamp: ISODateString
  components: ComponentHealth[]
}
