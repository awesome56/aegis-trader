import type {
  BrokerConnection,
  BrokerConnectionCreateInput,
  BrokerConnectionTestResult,
} from '~/types/autoTrading'
import { api } from './client'
import { isMockEnabled } from './config'
import { toBrokerConnection, toBrokerConnectionTest } from './adapters'
import type { RawBrokerConnection, RawBrokerConnectionTest } from './adapters/raw'

export const brokersService = {
  list: async (): Promise<BrokerConnection[]> => {
    if (isMockEnabled()) return []
    return (await api.get<RawBrokerConnection[]>('/brokers/connections')).map(toBrokerConnection)
  },
  create: async (input: BrokerConnectionCreateInput): Promise<BrokerConnection> => {
    if (isMockEnabled()) throw new Error('Broker connections are unavailable in mock mode')
    return toBrokerConnection(await api.post<RawBrokerConnection>('/brokers/connections', input))
  },
  update: async (id: string, input: Record<string, unknown>): Promise<BrokerConnection> => {
    if (isMockEnabled()) throw new Error('Broker connections are unavailable in mock mode')
    return toBrokerConnection(await api.put<RawBrokerConnection>(`/brokers/connections/${id}`, input))
  },
  remove: async (id: string): Promise<void> => {
    if (isMockEnabled()) return
    await api.delete(`/brokers/connections/${id}`)
  },
  test: async (id: string): Promise<BrokerConnectionTestResult> => {
    if (isMockEnabled()) return { ok: false, status: 'UNTESTED', detail: 'mock' }
    return toBrokerConnectionTest(
      await api.post<RawBrokerConnectionTest>(`/brokers/connections/${id}/test`),
    )
  },
  activate: async (id: string): Promise<BrokerConnection> => {
    if (isMockEnabled()) throw new Error('Broker connections are unavailable in mock mode')
    return toBrokerConnection(await api.post<RawBrokerConnection>(`/brokers/connections/${id}/activate`))
  },
}
