import type {
  AiProvider,
  AiProviderCatalog,
  AiProviderCatalogItem,
  AiProviderModel,
  AiProviderStatus,
  AiProviderTestResult,
} from '~/types/ai'
import { iso, isoOrNull } from './common'
import type { RawAiProvider, RawProviderCatalog, RawProviderCatalogItem, RawProviderTest } from './raw'

export function toAiProvider(raw: RawAiProvider): AiProvider {
  return {
    id: raw.id,
    provider: raw.provider,
    model: raw.model,
    base_url: raw.base_url,
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

function toModel(row: { id: string; label: string | null }): AiProviderModel {
  return { id: row.id, label: row.label }
}

export function toProviderTest(raw: RawProviderTest): AiProviderTestResult {
  return {
    ok: raw.ok,
    status: raw.status,
    detail: raw.detail,
    models: (raw.models ?? []).map(toModel),
  }
}

function toCatalogItem(raw: RawProviderCatalogItem): AiProviderCatalogItem {
  return {
    key: raw.key,
    requires_base_url: raw.requires_base_url,
    default_base_url: raw.default_base_url,
  }
}

export function toProviderCatalog(raw: RawProviderCatalog): AiProviderCatalog {
  return { items: (raw.items ?? []).map(toCatalogItem) }
}
