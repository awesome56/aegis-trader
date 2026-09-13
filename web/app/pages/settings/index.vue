<script setup lang="ts">
import { useAuth } from '~/composables/useAuth'
import { useTheme } from '~/composables/useTheme'
import { useSystemStatus } from '~/composables/useSystemStatus'
import { formatDateTime } from '~/utils/dates'
import type { ComponentStatus } from '~/types/system'

useHead({ title: 'Settings' })

const { user, logout } = useAuth()
const { preference, setTheme } = useTheme()
const { statusQuery, healthQuery } = useSystemStatus()

const status = computed(() => statusQuery.data.value)
const health = computed(() => healthQuery.data.value)

const themeOptions = [
  { value: 'dark' as const, label: 'Dark', icon: 'i-lucide-moon' },
  { value: 'light' as const, label: 'Light', icon: 'i-lucide-sun' },
  { value: 'system' as const, label: 'System', icon: 'i-lucide-monitor' },
]

function tone(value: ComponentStatus | undefined): 'success' | 'warning' | 'danger' | 'neutral' {
  if (value === 'healthy') return 'success'
  if (value === 'degraded') return 'warning'
  if (value === 'unhealthy') return 'danger'
  return 'neutral'
}
</script>

<template>
  <div>
    <PageHeader title="Settings" subtitle="Appearance, environment, system status and navigation." eyebrow="Configuration" />

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <section class="rounded-lg border border-default bg-elevated/20 p-4">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">Appearance</h2>
        <div class="mt-3 flex gap-2">
          <UButton
            v-for="option in themeOptions"
            :key="option.value"
            :icon="option.icon"
            size="sm"
            :variant="preference === option.value ? 'solid' : 'outline'"
            :color="preference === option.value ? 'primary' : 'neutral'"
            @click="setTheme(option.value)"
          >
            {{ option.label }}
          </UButton>
        </div>
      </section>

      <section class="rounded-lg border border-default bg-elevated/20 p-4">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">Trading environment</h2>
        <dl class="mt-3 space-y-1.5 text-sm">
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Mode</dt>
            <dd><StatusBadge :label="(status?.trading_mode ?? '—').toUpperCase()" :tone="status?.trading_mode === 'paper' ? 'paper' : 'live'" dot /></dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Kill switch</dt>
            <dd class="text-highlighted">{{ status?.kill_switch_state ?? '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Live trading</dt>
            <dd class="text-highlighted">{{ status?.live_trading_guard.allowed ? 'Allowed' : 'Locked' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Broker provider</dt>
            <dd class="text-highlighted">{{ status?.broker_provider ?? '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Market data</dt>
            <dd class="text-highlighted">{{ status?.market_data_provider ?? '—' }}</dd>
          </div>
        </dl>
        <p v-if="status && !status.live_trading_guard.allowed" class="mt-2 text-[11px] text-muted">
          {{ status.live_trading_guard.missing_requirements.length }} interlock requirement(s)
          must be satisfied before live trading can be enabled.
        </p>
      </section>

      <section class="rounded-lg border border-default bg-elevated/20 p-4 xl:col-span-2">
        <div class="flex items-center justify-between">
          <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">System status</h2>
          <span class="text-[11px] text-muted">{{ status?.app_name }} {{ status?.version }} · {{ status?.environment }}</span>
        </div>
        <LoadingSkeleton v-if="healthQuery.isLoading.value" class="mt-3" :rows="4" />
        <div v-else-if="health?.components.length" class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-muted">
              <tr>
                <th class="pb-2 font-medium">Component</th>
                <th class="pb-2 font-medium">Status</th>
                <th class="pb-2 text-right font-medium">Latency</th>
                <th class="pb-2 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="component in health.components" :key="component.name" class="border-t border-default">
                <td class="py-2 capitalize text-default">{{ component.name.replaceAll('_', ' ') }}</td>
                <td class="py-2"><StatusBadge :label="component.status" :tone="tone(component.status)" dot /></td>
                <td class="num py-2 text-right text-muted">{{ component.latency_ms === null ? '—' : `${component.latency_ms} ms` }}</td>
                <td class="py-2 text-muted">{{ component.detail ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="mt-3 text-xs text-muted">System health is unavailable.</p>
        <p v-if="status" class="mt-2 text-[11px] text-muted">Server time {{ formatDateTime(status.server_time) }}</p>
      </section>

      <AiProvidersSettings />

      <section class="rounded-lg border border-default bg-elevated/20 p-4">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">Manage</h2>
        <div class="mt-3 flex flex-wrap gap-2">
          <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-shield-alert" to="/risk">
            Manage Risk Settings
          </UButton>
          <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-workflow" to="/strategies">
            Manage Strategies
          </UButton>
          <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-file-text" to="/agent/proposals">
            Trade Proposals
          </UButton>
        </div>
        <p class="mt-2 text-[11px] text-muted">
          Risk limits and strategy enablement are managed on their dedicated pages.
        </p>
      </section>

      <section class="rounded-lg border border-default bg-elevated/20 p-4">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">Account</h2>
        <dl class="mt-3 space-y-1.5 text-sm">
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Email</dt>
            <dd class="truncate text-highlighted">{{ user?.email ?? '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Name</dt>
            <dd class="text-highlighted">{{ user?.full_name ?? '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Role</dt>
            <dd class="text-highlighted">{{ user?.is_superuser ? 'Owner' : 'User' }}</dd>
          </div>
        </dl>
        <p class="mt-3 text-[11px] text-muted">
          Credentials (broker, LLM, market-data) are configured server-side only and are never
          displayed or editable in the browser.
        </p>
        <UButton class="mt-3" color="error" variant="outline" size="sm" icon="i-lucide-log-out" @click="logout()">
          Sign out
        </UButton>
      </section>
    </div>
  </div>
</template>
