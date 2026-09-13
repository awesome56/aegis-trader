/** AI provider domain types (Phase 9). Raw tokens are never present here. */

import type { ISODateString } from './api'

export type AiProviderStatus = 'NOT_CONFIGURED' | 'UNTESTED' | 'CONNECTED' | 'ERROR' | 'DISABLED'

export interface AiProvider {
  id: string
  provider: string
  model: string
  base_url: string | null
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

export interface AiProviderCreateInput {
  provider: string
  model: string
  api_key: string
  base_url?: string
  enabled?: boolean
  make_default?: boolean
}

export interface AiProviderUpdateInput {
  model?: string
  api_key?: string
  base_url?: string
  enabled?: boolean
}

export interface AiProviderModel {
  id: string
  label: string | null
}

export interface AiProviderTestResult {
  ok: boolean
  status: string
  detail: string | null
  models: AiProviderModel[]
}

export interface AiProviderCatalogItem {
  key: string
  requires_base_url: boolean
  default_base_url: string | null
}

export interface AiProviderCatalog {
  items: AiProviderCatalogItem[]
}
