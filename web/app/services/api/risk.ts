import type { PageParams, Paginated } from '~/types/api'
import type { KillSwitchState } from '~/types/system'
import type { RiskEvent, RiskLimit, RiskSettings, RiskStatus } from '~/types/risk'
import { api } from './client'
import { isMockEnabled } from './config'
import {
  toRiskEvents,
  toRiskLimits,
  toRiskSettings,
  toRiskSettingsPatch,
  toRiskStatusFromOverview,
} from './adapters'
import type {
  RawRiskEvent,
  RawRiskOverview,
  RawRiskSettings,
  RawTradingStatus,
} from './adapters/raw'
import { mockRiskEvents, mockRiskLimits, mockRiskSettings, mockRiskStatus } from '~/mocks'

export interface TradingStatus {
  trading_state: KillSwitchState
  previous_state: KillSwitchState | null
  reason: string | null
  actor: string | null
  changed_at: string | null
}

function toTradingStatus(raw: RawTradingStatus): TradingStatus {
  return {
    trading_state: raw.trading_state as KillSwitchState,
    previous_state: raw.previous_state as KillSwitchState | null,
    reason: raw.reason,
    actor: raw.actor,
    changed_at: raw.changed_at,
  }
}

export const riskService = {
  status: async (): Promise<RiskStatus> => {
    if (isMockEnabled()) return mockRiskStatus()
    return toRiskStatusFromOverview(await api.get<RawRiskOverview>('/risk'))
  },
  limits: async (): Promise<RiskLimit[]> => {
    if (isMockEnabled()) return mockRiskLimits()
    const overview = await api.get<RawRiskOverview>('/risk')
    return toRiskLimits(overview.utilizations)
  },
  settings: async (): Promise<RiskSettings> => {
    if (isMockEnabled()) return mockRiskSettings()
    return toRiskSettings(await api.get<RawRiskSettings>('/risk/settings'))
  },
  updateSettings: async (settings: Partial<RiskSettings>): Promise<RiskSettings> => {
    if (isMockEnabled()) return { ...mockRiskSettings(), ...settings }
    const updated = await api.put<RawRiskSettings>('/risk/settings', toRiskSettingsPatch(settings))
    return toRiskSettings(updated)
  },
  events: async (_params: PageParams = {}): Promise<Paginated<RiskEvent>> => {
    if (isMockEnabled()) {
      const items = mockRiskEvents()
      return { items, total: items.length, page: 1, pageSize: items.length }
    }
    const items = toRiskEvents(await api.get<RawRiskEvent[]>('/risk/events'))
    return { items, total: items.length, page: 1, pageSize: items.length || 1 }
  },
  tradingStatus: async (): Promise<TradingStatus> => {
    if (isMockEnabled()) {
      return {
        trading_state: 'TRADING_ENABLED',
        previous_state: null,
        reason: null,
        actor: null,
        changed_at: null,
      }
    }
    return toTradingStatus(await api.get<RawTradingStatus>('/risk/trading-status'))
  },
  pause: async (reason?: string): Promise<TradingStatus> => {
    if (isMockEnabled()) return riskService.tradingStatus()
    return toTradingStatus(
      await api.post<RawTradingStatus>('/risk/pause', { confirm: true, reason: reason ?? 'manual' }),
    )
  },
  resume: async (): Promise<TradingStatus> => {
    if (isMockEnabled()) return riskService.tradingStatus()
    return toTradingStatus(
      await api.post<RawTradingStatus>('/risk/resume', { confirm: true }),
    )
  },
  enable: async (): Promise<TradingStatus> => {
    if (isMockEnabled()) return riskService.tradingStatus()
    return toTradingStatus(await api.post<RawTradingStatus>('/risk/enable', { confirm: true }))
  },
  disable: async (reason?: string): Promise<TradingStatus> => {
    if (isMockEnabled()) return riskService.tradingStatus()
    return toTradingStatus(
      await api.post<RawTradingStatus>('/risk/disable', { confirm: true, reason: reason ?? 'manual' }),
    )
  },
  emergencyStop: async (reason: string): Promise<TradingStatus> => {
    if (isMockEnabled()) return riskService.tradingStatus()
    return toTradingStatus(
      await api.post<RawTradingStatus>('/risk/emergency-stop', { confirm: true, reason }),
    )
  },
}
