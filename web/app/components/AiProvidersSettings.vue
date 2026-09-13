<script setup lang="ts">
import type { AiProvider, AiProviderStatus, AiProviderTestResult } from '~/types/ai'
import {
  useActivateAiProvider,
  useAiProviderCatalog,
  useAiProviders,
  useCreateAiProvider,
  useDeleteAiProvider,
  useTestAiProvider,
  useUpdateAiProvider,
} from '~/composables/useAiProviders'
import { formatDateTime } from '~/utils/dates'

const providersQuery = useAiProviders()
const catalogQuery = useAiProviderCatalog()
const createProvider = useCreateAiProvider()
const updateProvider = useUpdateAiProvider()
const deleteProvider = useDeleteAiProvider()
const testProvider = useTestAiProvider()
const activateProvider = useActivateAiProvider()

const providers = computed(() => providersQuery.data.value ?? [])
const catalog = computed(() => catalogQuery.data.value?.items ?? [])

const form = reactive({ provider: 'openai', model: '', api_key: '', base_url: '' })
const submitting = ref(false)
const errorMessage = ref<string | null>(null)
const testResults = reactive<Record<string, AiProviderTestResult>>({})
const replacing = ref<Record<string, string>>({})

const selectedCatalog = computed(() => catalog.value.find((item) => item.key === form.provider))
const requiresBaseUrl = computed(() => selectedCatalog.value?.requires_base_url ?? false)

const statusTone: Record<AiProviderStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
  CONNECTED: 'success',
  UNTESTED: 'neutral',
  NOT_CONFIGURED: 'neutral',
  ERROR: 'danger',
  DISABLED: 'warning',
}

function resetForm(): void {
  form.model = ''
  form.api_key = ''
  form.base_url = ''
}

async function addProvider(): Promise<void> {
  errorMessage.value = null
  if (!form.model.trim() || !form.api_key.trim()) {
    errorMessage.value = 'Model and API token are required.'
    return
  }
  if (requiresBaseUrl.value && !form.base_url.trim()) {
    errorMessage.value = 'This provider requires a base URL.'
    return
  }
  submitting.value = true
  try {
    await createProvider.mutateAsync({
      provider: form.provider,
      model: form.model.trim(),
      api_key: form.api_key.trim(),
      base_url: form.base_url.trim() || undefined,
      make_default: providers.value.length === 0,
    })
    resetForm()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not save provider.'
  } finally {
    submitting.value = false
  }
}

async function runTest(provider: AiProvider): Promise<void> {
  testResults[provider.id] = { ok: false, status: 'TESTING', detail: 'Testing…', models: [] }
  try {
    testResults[provider.id] = await testProvider.mutateAsync(provider.id)
  } catch (error) {
    testResults[provider.id] = {
      ok: false,
      status: 'ERROR',
      detail: error instanceof Error ? error.message : 'Test failed',
      models: [],
    }
  }
}

async function replaceKey(provider: AiProvider): Promise<void> {
  const value = (replacing.value[provider.id] ?? '').trim()
  if (!value) return
  await updateProvider.mutateAsync({ id: provider.id, input: { api_key: value } })
  replacing.value[provider.id] = ''
}

async function toggleEnabled(provider: AiProvider): Promise<void> {
  await updateProvider.mutateAsync({ id: provider.id, input: { enabled: !provider.enabled } })
}

async function remove(provider: AiProvider): Promise<void> {
  await deleteProvider.mutateAsync(provider.id)
}
</script>

<template>
  <section class="rounded-lg border border-default bg-elevated/20 p-4 xl:col-span-2">
    <div class="flex items-center justify-between">
      <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">AI Providers</h2>
      <span class="text-[11px] text-muted">Tokens are encrypted server-side and never shown again.</span>
    </div>

    <div v-if="errorMessage" class="mt-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
      {{ errorMessage }}
    </div>

    <LoadingSkeleton v-if="providersQuery.isLoading.value" class="mt-3" :rows="2" />
    <div v-else-if="providers.length" class="mt-3 space-y-3">
      <div v-for="provider in providers" :key="provider.id" class="rounded border border-default bg-elevated/30 p-3">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm font-medium text-highlighted">{{ provider.provider }}</span>
          <span class="num text-xs text-muted">{{ provider.model }}</span>
          <StatusBadge :label="provider.status" :tone="statusTone[provider.status]" dot />
          <StatusBadge v-if="provider.is_default" label="ACTIVE" tone="info" />
          <StatusBadge v-if="!provider.enabled" label="DISABLED" tone="warning" />
        </div>
        <p class="mt-1 text-[11px] text-muted">
          Key: <span class="num">{{ provider.api_key_masked ?? '—' }}</span>
          <span v-if="provider.base_url"> · {{ provider.base_url }}</span>
          <span v-if="provider.last_tested_at"> · tested {{ formatDateTime(provider.last_tested_at) }}</span>
        </p>
        <p v-if="provider.last_error" class="mt-1 text-[11px] text-down">{{ provider.last_error }}</p>
        <p v-if="testResults[provider.id]" class="mt-1 text-[11px]" :class="testResults[provider.id]?.ok ? 'text-up' : 'text-down'">
          Test: {{ testResults[provider.id]?.status }}<span v-if="testResults[provider.id]?.detail"> — {{ testResults[provider.id]?.detail }}</span>
        </p>
        <div class="mt-2 flex flex-wrap items-center gap-2">
          <UButton color="neutral" variant="outline" size="xs" :loading="testProvider.isPending.value" @click="runTest(provider)">
            Test Connection
          </UButton>
          <UButton color="neutral" variant="outline" size="xs" :disabled="provider.is_default || !provider.enabled" @click="activateProvider.mutate(provider.id)">
            Activate
          </UButton>
          <UButton color="neutral" variant="ghost" size="xs" @click="toggleEnabled(provider)">
            {{ provider.enabled ? 'Disable' : 'Enable' }}
          </UButton>
          <UButton color="error" variant="ghost" size="xs" @click="remove(provider)">Remove</UButton>
        </div>
        <div class="mt-2 flex items-center gap-2">
          <UInput
            v-model="replacing[provider.id]"
            type="password"
            size="xs"
            placeholder="Replace API key…"
            class="w-56"
          />
          <UButton color="neutral" variant="outline" size="xs" @click="replaceKey(provider)">Replace</UButton>
        </div>
      </div>
    </div>
    <p v-else class="mt-3 text-xs text-muted">No provider configured. Add one below to enable the agent.</p>

    <div class="mt-4 border-t border-default pt-3">
      <h3 class="text-xs font-semibold uppercase tracking-wide text-muted">Add provider</h3>
      <div class="mt-2 flex flex-wrap items-end gap-2">
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="ai-provider">Provider</label>
          <select id="ai-provider" v-model="form.provider" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
            <option v-for="item in catalog" :key="item.key" :value="item.key">{{ item.key }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="ai-model">Model</label>
          <UInput id="ai-model" v-model="form.model" placeholder="gpt-4o-mini" class="w-40" />
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="ai-key">API token</label>
          <UInput id="ai-key" v-model="form.api_key" type="password" placeholder="sk-…" class="w-48" />
        </div>
        <div v-if="requiresBaseUrl">
          <label class="mb-1 block text-[11px] text-muted" for="ai-base">Base URL</label>
          <UInput id="ai-base" v-model="form.base_url" placeholder="https://…/v1" class="w-56" />
        </div>
        <UButton color="primary" size="sm" :loading="submitting" @click="addProvider">Save provider</UButton>
      </div>
      <p class="mt-1 text-[11px] text-muted">
        The token is sent once to the backend, encrypted at rest, and never stored in this browser.
      </p>
    </div>
  </section>
</template>
