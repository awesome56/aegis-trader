import type {
  AutoTradingAccountStatus,
  AutoTradingPolicy,
  AutoTradingStatus,
  BrokerConnection,
  BrokerConnectionTestResult,
  BrokerEnvironment,
} from '~/types/autoTrading'
import type { AiProviderStatus } from '~/types/ai'
import { iso, isoOrNull, numOrNull } from './common'
import type {
  RawAutoTradingAccountStatus,
  RawAutoTradingPolicy,
  RawAutoTradingStatus,
  RawBrokerConnection,
  RawBrokerConnectionTest,
} from './raw'

export function toBrokerConnection(raw: RawBrokerConnection): BrokerConnection {
  return {
    id: raw.id,
    provider: raw.provider,
    environment: raw.environment as BrokerEnvironment,
    account_external_id: raw.account_external_id,
    configured: raw.configured,
    api_key_masked: raw.api_key_masked,
    enabled: raw.enabled,
    is_default: raw.is_default,
    status: raw.status as AiProviderStatus,
    last_tested_at: isoOrNull(raw.last_tested_at),
    last_error: raw.last_error,
    created_at: iso(raw.created_at),
    updated_at: iso(raw.updated_at),
  }
}

export function toBrokerConnectionTest(raw: RawBrokerConnectionTest): BrokerConnectionTestResult {
  return { ok: raw.ok, status: raw.status, detail: raw.detail }
}

export function toAutoTradingPolicy(raw: RawAutoTradingPolicy): AutoTradingPolicy {
  return {
    id: raw.id,
    broker_account_id: raw.broker_account_id,
    environment: raw.environment as BrokerEnvironment,
    enabled: raw.enabled,
    allow_open: raw.allow_open,
    allow_add: raw.allow_add,
    allow_reduce: raw.allow_reduce,
    allow_close: raw.allow_close,
    allow_cancel: raw.allow_cancel,
    allow_replace: raw.allow_replace,
    allow_manage_manual_positions: raw.allow_manage_manual_positions,
    allow_manage_manual_orders: raw.allow_manage_manual_orders,
    allowed_asset_classes: raw.allowed_asset_classes,
    allowed_symbols: raw.allowed_symbols,
    max_trade_notional: numOrNull(raw.max_trade_notional),
    max_position_notional: numOrNull(raw.max_position_notional),
    max_trades_per_day: raw.max_trades_per_day,
    cooldown_seconds: raw.cooldown_seconds,
    min_agent_confidence: numOrNull(raw.min_agent_confidence),
    require_strategy_signal: raw.require_strategy_signal,
    min_strategy_confidence: numOrNull(raw.min_strategy_confidence),
    notes: raw.notes,
  }
}

function toAccount(raw: RawAutoTradingAccountStatus): AutoTradingAccountStatus {
  return {
    broker_account_id: raw.broker_account_id,
    provider: raw.provider,
    account_name: raw.account_name,
    environment: raw.environment as BrokerEnvironment,
    enabled: raw.enabled,
    trading_state: raw.trading_state,
    policy: toAutoTradingPolicy(raw.policy),
  }
}

export function toAutoTradingStatus(raw: RawAutoTradingStatus): AutoTradingStatus {
  return {
    live_trading_allowed: raw.live_trading_allowed,
    demo_any_enabled: raw.demo_any_enabled,
    live_any_enabled: raw.live_any_enabled,
    accounts: (raw.accounts ?? []).map(toAccount),
  }
}
