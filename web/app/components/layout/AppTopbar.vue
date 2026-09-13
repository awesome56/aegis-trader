<script setup lang="ts">
import { onClickOutside } from '@vueuse/core'
import { useAppStore } from '~/stores/app'
import { useAuth } from '~/composables/useAuth'
import { useTheme } from '~/composables/useTheme'
import { useSystemStatus } from '~/composables/useSystemStatus'
import type { ComponentStatus } from '~/types/system'

const app = useAppStore()
const router = useRouter()
const { user, logout } = useAuth()
const { preference, cycle } = useTheme()
const { statusQuery, healthQuery } = useSystemStatus()

const status = computed(() => statusQuery.data.value)
const agentEnabled = computed(() => status.value?.agent_enabled ?? false)
const brokerProvider = computed(() => status.value?.broker_provider ?? '—')
const marketProvider = computed(() => status.value?.market_data_provider ?? '—')

function componentStatus(name: string): ComponentStatus | undefined {
  return healthQuery.data.value?.components.find((component) => component.name === name)?.status
}

function statusTone(value: ComponentStatus | undefined): 'success' | 'warning' | 'danger' | 'neutral' {
  if (value === 'healthy') return 'success'
  if (value === 'degraded') return 'warning'
  if (value === 'unhealthy') return 'danger'
  return 'neutral'
}

const brokerStatus = computed(() => componentStatus('broker'))
const marketStatus = computed(() => componentStatus('market_data'))

const userMenuOpen = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)
onClickOutside(userMenuRef, () => {
  userMenuOpen.value = false
})

const themeIcon = computed(() =>
  preference.value === 'dark'
    ? 'i-lucide-moon'
    : preference.value === 'light'
      ? 'i-lucide-sun'
      : 'i-lucide-monitor',
)

async function signOut(): Promise<void> {
  userMenuOpen.value = false
  await logout()
  await router.push('/login')
}
</script>

<template>
  <header
    class="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-default bg-default/90 px-3 backdrop-blur lg:px-4"
  >
    <!-- Mobile nav trigger -->
    <UButton
      class="lg:hidden"
      color="neutral"
      variant="ghost"
      size="sm"
      icon="i-lucide-menu"
      aria-label="Open navigation"
      @click="app.toggleMobileNav()"
    />

    <!-- Brand -->
    <NuxtLink
      to="/dashboard"
      class="flex shrink-0 items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
    >
      <span
        class="flex h-7 w-7 items-center justify-center rounded-md bg-primary/15 text-primary"
        aria-hidden="true"
      >
        <UIcon name="i-lucide-activity" class="h-4 w-4" />
      </span>
      <span class="hidden text-sm font-semibold tracking-tight text-highlighted sm:inline">
        Aegis Trader
      </span>
    </NuxtLink>

    <!-- Quick search -->
    <button
      type="button"
      class="hidden items-center gap-2 rounded-md border border-default bg-elevated/30 px-2.5 py-1.5 text-xs text-muted transition-colors hover:border-accented hover:text-highlighted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 md:flex"
      aria-label="Open quick navigation"
      @click="app.toggleCommandPalette()"
    >
      <UIcon name="i-lucide-search" class="h-3.5 w-3.5" aria-hidden="true" />
      <span>Search</span>
      <kbd class="rounded border border-default px-1 py-0.5 text-[10px]">⌘K</kbd>
    </button>

    <div class="flex-1" />

    <!-- Trading mode is always visible -->
    <AutoTradingBadge />
    <TradingModeBadge />

    <div class="hidden items-center gap-2 xl:flex">
      <StatusBadge
        :label="`Agent ${agentEnabled ? 'On' : 'Off'}`"
        :tone="agentEnabled ? 'success' : 'neutral'"
        dot
      />
      <StatusBadge
        :label="`Broker · ${brokerProvider}`"
        :tone="statusTone(brokerStatus)"
        dot
      />
      <StatusBadge
        :label="`Market · ${marketProvider}`"
        :tone="statusTone(marketStatus)"
        dot
      />
    </div>

    <ConnectionStatus />

    <!-- Notifications -->
    <NotificationBell />

    <!-- Theme -->
    <UButton
      color="neutral"
      variant="ghost"
      size="sm"
      :icon="themeIcon"
      :aria-label="`Theme: ${preference}. Activate to change.`"
      @click="cycle()"
    />

    <!-- User menu -->
    <div ref="userMenuRef" class="relative">
      <UButton
        color="neutral"
        variant="ghost"
        size="sm"
        icon="i-lucide-user"
        :aria-label="`Account menu for ${user?.email ?? 'user'}`"
        :aria-expanded="userMenuOpen"
        @click="userMenuOpen = !userMenuOpen"
      />
      <div
        v-if="userMenuOpen"
        class="absolute right-0 z-40 mt-1 w-56 rounded-lg border border-default bg-default py-1 shadow-xl"
        role="menu"
      >
        <div class="border-b border-default px-3 py-2">
          <p class="truncate text-xs font-medium text-highlighted">
            {{ user?.full_name ?? 'Signed in' }}
          </p>
          <p class="truncate text-[11px] text-muted">{{ user?.email }}</p>
        </div>
        <button
          type="button"
          role="menuitem"
          class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-muted hover:bg-elevated hover:text-highlighted"
          @click="userMenuOpen = false; router.push('/settings')"
        >
          <UIcon name="i-lucide-settings" class="h-4 w-4" aria-hidden="true" /> Settings
        </button>
        <button
          type="button"
          role="menuitem"
          class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-rose-400 hover:bg-elevated"
          @click="signOut"
        >
          <UIcon name="i-lucide-log-out" class="h-4 w-4" aria-hidden="true" /> Sign out
        </button>
      </div>
    </div>
  </header>
</template>
