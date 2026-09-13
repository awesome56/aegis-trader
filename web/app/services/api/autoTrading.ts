import type { AutoTradingPolicy, AutoTradingStatus } from '~/types/autoTrading'
import { api } from './client'
import { isMockEnabled } from './config'
import { toAutoTradingPolicy, toAutoTradingStatus } from './adapters'
import type { RawAutoTradingPolicy, RawAutoTradingStatus } from './adapters/raw'

export const autoTradingService = {
  status: async (): Promise<AutoTradingStatus> => {
    if (isMockEnabled()) {
      return {
        live_trading_allowed: false,
        demo_any_enabled: false,
        live_any_enabled: false,
        accounts: [],
      }
    }
    return toAutoTradingStatus(await api.get<RawAutoTradingStatus>('/auto-trading/status'))
  },
  policy: async (accountId: string): Promise<AutoTradingPolicy> => {
    if (isMockEnabled()) throw new Error('Auto trading is unavailable in mock mode')
    return toAutoTradingPolicy(
      await api.get<RawAutoTradingPolicy>(`/auto-trading/${accountId}/policy`),
    )
  },
  updatePolicy: async (
    accountId: string,
    patch: Partial<AutoTradingPolicy>,
  ): Promise<AutoTradingPolicy> => {
    if (isMockEnabled()) throw new Error('Auto trading is unavailable in mock mode')
    return toAutoTradingPolicy(
      await api.put<RawAutoTradingPolicy>(`/auto-trading/${accountId}/policy`, patch),
    )
  },
  enable: async (accountId: string, confirm: boolean, phrase?: string): Promise<AutoTradingPolicy> => {
    if (isMockEnabled()) throw new Error('Auto trading is unavailable in mock mode')
    return toAutoTradingPolicy(
      await api.post<RawAutoTradingPolicy>(`/auto-trading/${accountId}/enable`, { confirm, phrase }),
    )
  },
  disable: async (accountId: string): Promise<AutoTradingPolicy> => {
    if (isMockEnabled()) throw new Error('Auto trading is unavailable in mock mode')
    return toAutoTradingPolicy(
      await api.post<RawAutoTradingPolicy>(`/auto-trading/${accountId}/disable`),
    )
  },
}
