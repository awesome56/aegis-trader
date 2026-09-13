<script setup lang="ts">
import type { AutoTradingAccountStatus, BrokerEnvironment } from '~/types/autoTrading'
import {
  useAutoTradingStatus,
  useDisableAutoTrading,
  useEnableAutoTrading,
  useUpdateAutoTradingPolicy,
} from '~/composables/useAutoTrading'

const statusQuery = useAutoTradingStatus()
const enableAuto = useEnableAutoTrading()
const disableAuto = useDisableAutoTrading()
const updatePolicy = useUpdateAutoTradingPolicy()

const status = computed(() => statusQuery.data.value ?? null)
const accounts = computed(() => status.value?.accounts ?? [])

const LIVE_PHRASE = 'ENABLE LIVE AUTO TRADING'
const ASSET_CLASSES = ['EQUITY', 'ETF', 'CRYPTO', 'FOREX']
const PERMISSIONS: { key: keyof AutoTradingAccountStatus['policy']; label: string }[] = [
  { key: 'allow_open', label: 'Open' },
  { key: 'allow_add', label: 'Add' },
  { key: 'allow_reduce', label: 'Reduce' },
  { key: 'allow_close', label: 'Close' },
  { key: 'allow_cancel', label: 'Cancel' },
  { key: 'allow_replace', label: 'Replace' },
]

const dialog = reactive({ open: false, accountId: '', environment: 'DEMO' as BrokerEnvironment })
const errorMessage = ref<string | null>(null)

function enable(account: AutoTradingAccountStatus): void {
  errorMessage.value = null
  dialog.accountId = account.broker_account_id
  dialog.environment = account.environment
  if (account.environment === 'LIVE') {
    dialog.open = true
  } else {
    void enableAuto
      .mutateAsync({ accountId: account.broker_account_id, confirm: true })
      .catch((error: unknown) => {
        errorMessage.value = error instanceof Error ? error.message : 'Could not enable.'
      })
  }
}

async function confirmLive(): Promise<void> {
  try {
    await enableAuto.mutateAsync({ accountId: dialog.accountId, confirm: true, phrase: LIVE_PHRASE })
    dialog.open = false
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not enable live auto trading.'
  }
}

function togglePermission(account: AutoTradingAccountStatus, key: string): void {
  const policy = account.policy
  const current = policy[key as keyof typeof policy] as boolean
  void updatePolicy.mutateAsync({
    accountId: account.broker_account_id,
    patch: { [key]: !current } as never,
  })
}

function toggleAssetClass(account: AutoTradingAccountStatus, assetClass: string): void {
  const current = new Set(account.policy.allowed_asset_classes ?? ASSET_CLASSES)
  if (current.has(assetClass)) current.delete(assetClass)
  else current.add(assetClass)
  void updatePolicy.mutateAsync({
    accountId: account.broker_account_id,
    patch: { allowed_asset_classes: current.size ? [...current] : null } as never,
  })
}
</script>

<template>
  <section class="rounded-lg border border-default bg-elevated/20 p-4 xl:col-span-2">
    <div class="flex items-center justify-between">
      <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">Autonomous trading</h2>
      <span class="text-[11px] text-muted">
        Live trading allowed by server: {{ status?.live_trading_allowed ? 'yes' : 'no' }}
      </span>
    </div>

    <div v-if="errorMessage" class="mt-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
      {{ errorMessage }}
    </div>
    <div
      v-if="status?.live_any_enabled"
      class="mt-3 rounded-md border border-rose-500/50 bg-rose-500/10 px-3 py-2 text-xs font-semibold text-rose-300"
    >
      LIVE AUTO TRADING ENABLED
    </div>

    <LoadingSkeleton v-if="statusQuery.isLoading.value" class="mt-3" :rows="2" />
    <div v-else-if="accounts.length" class="mt-3 space-y-3">
      <div v-for="account in accounts" :key="account.broker_account_id" class="rounded border border-default bg-elevated/30 p-3">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm font-medium text-highlighted">{{ account.account_name }}</span>
          <StatusBadge :label="`${account.environment} AUTO`" :tone="account.enabled ? (account.environment === 'LIVE' ? 'danger' : 'info') : 'neutral'" dot />
          <StatusBadge :label="account.enabled ? 'ON' : 'OFF'" :tone="account.enabled ? 'success' : 'neutral'" />
          <span class="text-[11px] text-muted">{{ account.provider }} · {{ account.trading_state.replaceAll('_', ' ') }}</span>
        </div>

        <div class="mt-2 flex flex-wrap items-center gap-2">
          <UButton
            v-if="!account.enabled"
            color="primary"
            size="xs"
            :disabled="account.environment === 'LIVE' && !status?.live_trading_allowed"
            :loading="enableAuto.isPending.value"
            @click="enable(account)"
          >
            Enable {{ account.environment }} auto trading
          </UButton>
          <UButton
            v-else
            color="warning"
            variant="outline"
            size="xs"
            :loading="disableAuto.isPending.value"
            @click="disableAuto.mutate(account.broker_account_id)"
          >
            Disable
          </UButton>
        </div>

        <div class="mt-3">
          <p class="text-[11px] uppercase tracking-wide text-muted">Agent permissions</p>
          <div class="mt-1 flex flex-wrap gap-2">
            <label
              v-for="permission in PERMISSIONS"
              :key="String(permission.key)"
              class="flex items-center gap-1 text-[11px] text-default"
            >
              <input
                type="checkbox"
                :checked="Boolean(account.policy[permission.key])"
                @change="togglePermission(account, String(permission.key))"
              />
              {{ permission.label }}
            </label>
          </div>
        </div>

        <div class="mt-2 flex flex-wrap gap-3">
          <label class="flex items-center gap-1 text-[11px] text-default">
            <input type="checkbox" :checked="account.policy.allow_manage_manual_positions" @change="togglePermission(account, 'allow_manage_manual_positions')" />
            Manage manual positions
          </label>
          <label class="flex items-center gap-1 text-[11px] text-default">
            <input type="checkbox" :checked="account.policy.allow_manage_manual_orders" @change="togglePermission(account, 'allow_manage_manual_orders')" />
            Manage manual orders
          </label>
        </div>

        <div class="mt-2">
          <p class="text-[11px] uppercase tracking-wide text-muted">Allowed asset classes</p>
          <div class="mt-1 flex flex-wrap gap-2">
            <label v-for="assetClass in ASSET_CLASSES" :key="assetClass" class="flex items-center gap-1 text-[11px] text-default">
              <input
                type="checkbox"
                :checked="(account.policy.allowed_asset_classes ?? ASSET_CLASSES).includes(assetClass)"
                @change="toggleAssetClass(account, assetClass)"
              />
              {{ assetClass }}
            </label>
          </div>
        </div>

        <div class="mt-2 flex items-end gap-2">
          <div class="min-w-48 flex-1">
            <label class="mb-1 block text-[11px] text-muted">Allowed symbols (comma separated; empty = all)</label>
            <UInput
              :model-value="(account.policy.allowed_symbols ?? []).join(', ')"
              placeholder="BTC/USD, EUR/USD"
              @update:model-value="(value: string) => updatePolicy.mutate({ accountId: account.broker_account_id, patch: { allowed_symbols: value.trim() ? value.split(',').map((s: string) => s.trim().toUpperCase()) : null } })"
            />
          </div>
        </div>
      </div>
    </div>
    <p v-else class="mt-3 text-xs text-muted">No broker account available yet.</p>

    <ConfirmationDialog
      v-model:open="dialog.open"
      title="Enable LIVE auto trading"
      description="The agent will be able to place real orders on a LIVE account. This is irreversible without disabling."
      :consequences="['Real money can be traded', 'Every action still passes the Risk Engine and safety gateway', 'Type the phrase to confirm']"
      tone="danger"
      confirm-label="Enable live auto trading"
      :confirm-phrase="LIVE_PHRASE"
      :loading="enableAuto.isPending.value"
      @confirm="confirmLive"
    />
  </section>
</template>
