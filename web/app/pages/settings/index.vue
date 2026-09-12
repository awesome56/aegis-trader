<script setup lang="ts">
import { useAuth } from '~/composables/useAuth'
import { useTheme } from '~/composables/useTheme'
import { useSystemStatus } from '~/composables/useSystemStatus'

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
</script>

<template>
  <div>
    <PageHeader title="Settings" subtitle="Appearance, account and system information." eyebrow="Configuration" />

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
        <UButton class="mt-3" color="error" variant="outline" size="sm" icon="i-lucide-log-out" @click="logout()">
          Sign out
        </UButton>
      </section>

      <section class="rounded-lg border border-default bg-elevated/20 p-4">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">Trading</h2>
        <dl class="mt-3 space-y-1.5 text-sm">
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Mode</dt>
            <dd><StatusBadge :label="(status?.trading_mode ?? '—').toUpperCase()" :tone="status?.trading_mode === 'paper' ? 'paper' : 'live'" /></dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Kill switch</dt>
            <dd class="text-highlighted">{{ status?.kill_switch_state ?? '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Live trading</dt>
            <dd class="text-highlighted">
              {{ status?.live_trading_guard.allowed ? 'Allowed' : 'Locked' }}
            </dd>
          </div>
        </dl>
        <p v-if="status && !status.live_trading_guard.allowed" class="mt-2 text-[11px] text-muted">
          {{ status.live_trading_guard.missing_requirements.length }} interlock requirement(s)
          must be satisfied before live trading can be enabled.
        </p>
      </section>

      <section class="rounded-lg border border-default bg-elevated/20 p-4">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-muted">System</h2>
        <p class="mt-2 text-[11px] text-muted">
          Credentials (broker, LLM, market-data) are configured server-side only and are
          never displayed or stored in the browser.
        </p>
        <dl class="mt-3 space-y-1.5 text-sm">
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Broker</dt>
            <dd class="text-highlighted">{{ status?.broker_provider ?? '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Market data</dt>
            <dd class="text-highlighted">{{ status?.market_data_provider ?? '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">Health</dt>
            <dd class="text-highlighted">{{ health?.status ?? '—' }}</dd>
          </div>
        </dl>
      </section>
    </div>
  </div>
</template>
