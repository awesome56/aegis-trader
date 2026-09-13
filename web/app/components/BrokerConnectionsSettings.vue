<script setup lang="ts">
import type { BrokerConnection, BrokerEnvironment } from '~/types/autoTrading'
import type { AiProviderStatus } from '~/types/ai'
import {
  useActivateBrokerConnection,
  useBrokerConnections,
  useCreateBrokerConnection,
  useDeleteBrokerConnection,
  useTestBrokerConnection,
} from '~/composables/useAutoTrading'
import { formatDateTime } from '~/utils/dates'

const connectionsQuery = useBrokerConnections()
const createConnection = useCreateBrokerConnection()
const testConnection = useTestBrokerConnection()
const activateConnection = useActivateBrokerConnection()
const deleteConnection = useDeleteBrokerConnection()

const PROVIDERS = ['paper', 'alpaca', 'oanda', 'kraken', 'binance', 'coinbase', 'interactive_brokers']
const ENVIRONMENTS: BrokerEnvironment[] = ['DEMO', 'LIVE']

const form = reactive({
  provider: 'paper',
  environment: 'DEMO' as BrokerEnvironment,
  account_external_id: '',
  api_key: '',
  api_secret: '',
  access_token: '',
})
const errorMessage = ref<string | null>(null)
const testResults = reactive<Record<string, string>>({})

const connections = computed(() => connectionsQuery.data.value ?? [])

const statusTone: Record<AiProviderStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
  CONNECTED: 'success',
  UNTESTED: 'neutral',
  NOT_CONFIGURED: 'neutral',
  ERROR: 'danger',
  DISABLED: 'warning',
}

async function addConnection(): Promise<void> {
  errorMessage.value = null
  try {
    await createConnection.mutateAsync({
      provider: form.provider,
      environment: form.environment,
      account_external_id: form.account_external_id || undefined,
      api_key: form.api_key || undefined,
      api_secret: form.api_secret || undefined,
      access_token: form.access_token || undefined,
      make_default: connections.value.length === 0,
    })
    form.api_key = ''
    form.api_secret = ''
    form.access_token = ''
    form.account_external_id = ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not save connection.'
  }
}

async function runTest(connection: BrokerConnection): Promise<void> {
  testResults[connection.id] = 'TESTING…'
  try {
    const result = await testConnection.mutateAsync(connection.id)
    testResults[connection.id] = `${result.status}${result.detail ? ` — ${result.detail}` : ''}`
  } catch (error) {
    testResults[connection.id] = error instanceof Error ? error.message : 'Test failed'
  }
}
</script>

<template>
  <section class="rounded-lg border border-default bg-elevated/20 p-4 xl:col-span-2">
    <div class="flex items-center justify-between">
      <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">Broker connections</h2>
      <span class="text-[11px] text-muted">Secrets are encrypted server-side and never shown again.</span>
    </div>

    <div v-if="errorMessage" class="mt-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
      {{ errorMessage }}
    </div>

    <LoadingSkeleton v-if="connectionsQuery.isLoading.value" class="mt-3" :rows="2" />
    <div v-else-if="connections.length" class="mt-3 space-y-3">
      <div v-for="connection in connections" :key="connection.id" class="rounded border border-default bg-elevated/30 p-3">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm font-medium text-highlighted">{{ connection.provider }}</span>
          <StatusBadge :label="connection.environment" :tone="connection.environment === 'LIVE' ? 'danger' : 'info'" />
          <StatusBadge :label="connection.status" :tone="statusTone[connection.status]" dot />
          <StatusBadge v-if="connection.is_default" label="DEFAULT" tone="neutral" />
          <StatusBadge v-if="!connection.enabled" label="DISABLED" tone="warning" />
        </div>
        <p class="mt-1 text-[11px] text-muted">
          Key: <span class="num">{{ connection.api_key_masked ?? '—' }}</span>
          <span v-if="connection.account_external_id"> · account {{ connection.account_external_id }}</span>
          <span v-if="connection.last_tested_at"> · tested {{ formatDateTime(connection.last_tested_at) }}</span>
        </p>
        <p v-if="connection.last_error" class="mt-1 text-[11px] text-down">{{ connection.last_error }}</p>
        <p v-if="testResults[connection.id]" class="mt-1 text-[11px] text-muted">{{ testResults[connection.id] }}</p>
        <div class="mt-2 flex flex-wrap gap-2">
          <UButton color="neutral" variant="outline" size="xs" @click="runTest(connection)">Test Connection</UButton>
          <UButton color="neutral" variant="outline" size="xs" :disabled="connection.is_default" @click="activateConnection.mutate(connection.id)">
            Set default
          </UButton>
          <UButton color="error" variant="ghost" size="xs" @click="deleteConnection.mutate(connection.id)">Remove</UButton>
        </div>
      </div>
    </div>
    <p v-else class="mt-3 text-xs text-muted">No broker connection configured. The internal paper broker is used by default.</p>

    <div class="mt-4 border-t border-default pt-3">
      <h3 class="text-xs font-semibold uppercase tracking-wide text-muted">Add connection</h3>
      <div class="mt-2 flex flex-wrap items-end gap-2">
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bc-provider">Provider</label>
          <select id="bc-provider" v-model="form.provider" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
            <option v-for="provider in PROVIDERS" :key="provider" :value="provider">{{ provider }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bc-env">Environment</label>
          <select id="bc-env" v-model="form.environment" class="rounded border border-default bg-elevated/40 px-2 py-1.5 text-xs text-default">
            <option v-for="env in ENVIRONMENTS" :key="env" :value="env">{{ env }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bc-account">Account ID</label>
          <UInput id="bc-account" v-model="form.account_external_id" class="w-36" />
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bc-key">API key</label>
          <UInput id="bc-key" v-model="form.api_key" type="password" class="w-40" />
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bc-secret">API secret</label>
          <UInput id="bc-secret" v-model="form.api_secret" type="password" class="w-40" />
        </div>
        <div>
          <label class="mb-1 block text-[11px] text-muted" for="bc-token">Access token</label>
          <UInput id="bc-token" v-model="form.access_token" type="password" class="w-40" />
        </div>
        <UButton color="primary" size="sm" :loading="createConnection.isPending.value" @click="addConnection">
          Save connection
        </UButton>
      </div>
      <p class="mt-1 text-[11px] text-muted">
        LIVE connections require <span class="num">LIVE_TRADING_ALLOWED=true</span> on the server. External adapters are not implemented yet.
      </p>
    </div>
  </section>
</template>
