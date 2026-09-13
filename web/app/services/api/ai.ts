import type {
  AiProvider,
  AiProviderCatalog,
  AiProviderCreateInput,
  AiProviderTestResult,
  AiProviderUpdateInput,
} from '~/types/ai'
import { api } from './client'
import { isMockEnabled } from './config'
import { toAiProvider, toProviderCatalog, toProviderTest } from './adapters'
import type { RawAiProvider, RawProviderCatalog, RawProviderTest } from './adapters/raw'

export const aiService = {
  supported: async (): Promise<AiProviderCatalog> => {
    if (isMockEnabled()) return { items: [] }
    return toProviderCatalog(await api.get<RawProviderCatalog>('/ai/providers/supported'))
  },
  list: async (): Promise<AiProvider[]> => {
    if (isMockEnabled()) return []
    return (await api.get<RawAiProvider[]>('/ai/providers')).map(toAiProvider)
  },
  create: async (input: AiProviderCreateInput): Promise<AiProvider> => {
    if (isMockEnabled()) throw new Error('AI providers are unavailable in mock mode')
    return toAiProvider(await api.post<RawAiProvider>('/ai/providers', input))
  },
  update: async (id: string, input: AiProviderUpdateInput): Promise<AiProvider> => {
    if (isMockEnabled()) throw new Error('AI providers are unavailable in mock mode')
    return toAiProvider(await api.put<RawAiProvider>(`/ai/providers/${id}`, input))
  },
  remove: async (id: string): Promise<void> => {
    if (isMockEnabled()) return
    await api.delete(`/ai/providers/${id}`)
  },
  test: async (id: string): Promise<AiProviderTestResult> => {
    if (isMockEnabled()) return { ok: false, status: 'UNTESTED', detail: 'mock', models: [] }
    return toProviderTest(await api.post<RawProviderTest>(`/ai/providers/${id}/test`))
  },
  activate: async (id: string): Promise<AiProvider> => {
    if (isMockEnabled()) throw new Error('AI providers are unavailable in mock mode')
    return toAiProvider(await api.post<RawAiProvider>(`/ai/providers/${id}/activate`))
  },
}
