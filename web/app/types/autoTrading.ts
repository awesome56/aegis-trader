/** Phase 10 auto-trading / broker connection domain types. */

import type { ISODateString, Numeric } from './api'
import type { AiProviderStatus } from './ai'

export type BrokerEnvironment = 'DEMO' | 'LIVE'

export interface BrokerConnection {
  id: string
  provider: string
  environment: BrokerEnvironment
  account_external_id: string | null
  configured: boolean
  api_key_masked: string | null
  enabled: boolean
  is_default: boolean
  status: AiProviderStatus
  last_tested_at: ISODateString | null
  last_error: string | null
  created_at: ISODateString
  updated_at: ISODateString
}

export interface BrokerConnectionCreateInput {
  provider: string
  environment: BrokerEnvironment
  account_external_id?: string
  api_key?: string
  api_secret?: string
  access_token?: string
  enabled?: boolean
  make_default?: boolean
}

export interface BrokerConnectionTestResult {
  ok: boolean
  status: string
  detail: string | null
}

export interface AutoTradingPolicy {
  id: string | null
  broker_account_id: string | null
  environment: BrokerEnvironment
  enabled: boolean
  allow_open: boolean
  allow_add: boolean
  allow_reduce: boolean
  allow_close: boolean
  allow_cancel: boolean
  allow_replace: boolean
  allow_manage_manual_positions: boolean
  allow_manage_manual_orders: boolean
  allowed_asset_classes: string[] | null
  allowed_symbols: string[] | null
  max_trade_notional: Numeric | null
  max_position_notional: Numeric | null
  max_trades_per_day: number | null
  cooldown_seconds: number
  min_agent_confidence: Numeric | null
  require_strategy_signal: boolean
  min_strategy_confidence: Numeric | null
  notes: string | null
}

export interface AutoTradingAccountStatus {
  broker_account_id: string
  provider: string
  account_name: string
  environment: BrokerEnvironment
  enabled: boolean
  trading_state: string
  policy: AutoTradingPolicy
}

export interface AutoTradingStatus {
  live_trading_allowed: boolean
  demo_any_enabled: boolean
  live_any_enabled: boolean
  accounts: AutoTradingAccountStatus[]
}
