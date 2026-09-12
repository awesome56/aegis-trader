<script setup lang="ts">
import { primaryNav, isActiveRoute } from '~/utils/navigation'
import { useAppStore } from '~/stores/app'

const app = useAppStore()
const route = useRoute()

const collapsed = computed(() => app.sidebarCollapsed)

function isActive(target: string): boolean {
  return isActiveRoute(route.path, target)
}
</script>

<template>
  <!-- Desktop sidebar -->
  <aside
    class="sticky top-14 hidden h-[calc(100vh-3.5rem)] shrink-0 flex-col border-r border-default bg-elevated/10 transition-[width] duration-200 lg:flex"
    :class="collapsed ? 'w-[60px]' : 'w-56'"
    aria-label="Primary navigation"
  >
    <nav class="flex-1 space-y-0.5 overflow-y-auto p-2">
      <NuxtLink
        v-for="item in primaryNav"
        :key="item.to"
        :to="item.to"
        :title="collapsed ? item.label : undefined"
        :aria-current="isActive(item.to) ? 'page' : undefined"
        class="group flex items-center gap-3 rounded-md px-2.5 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
        :class="
          isActive(item.to)
            ? 'bg-primary/10 text-primary'
            : 'text-muted hover:bg-elevated hover:text-highlighted'
        "
      >
        <UIcon :name="item.icon" class="h-4 w-4 shrink-0" aria-hidden="true" />
        <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
        <span v-else class="sr-only">{{ item.label }}</span>
      </NuxtLink>
    </nav>

    <div class="border-t border-default p-2">
      <button
        type="button"
        class="flex w-full items-center gap-3 rounded-md px-2.5 py-2 text-sm text-muted transition-colors hover:bg-elevated hover:text-highlighted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
        :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :aria-expanded="!collapsed"
        @click="app.toggleSidebar()"
      >
        <UIcon
          :name="collapsed ? 'i-lucide-chevrons-right' : 'i-lucide-chevrons-left'"
          class="h-4 w-4 shrink-0"
          aria-hidden="true"
        />
        <span v-if="!collapsed">Collapse</span>
      </button>
    </div>
  </aside>

  <!-- Mobile drawer -->
  <div v-if="app.mobileNavOpen" class="lg:hidden">
    <div class="fixed inset-0 z-40 bg-black/60" @click="app.closeMobileNav()" />
    <aside
      class="fixed inset-y-0 left-0 z-50 w-64 border-r border-default bg-default p-3 shadow-2xl"
      aria-label="Primary navigation"
    >
      <div class="mb-3 flex items-center justify-between">
        <span class="text-sm font-semibold text-highlighted">Navigation</span>
        <UButton
          color="neutral"
          variant="ghost"
          size="xs"
          icon="i-lucide-x"
          aria-label="Close navigation"
          @click="app.closeMobileNav()"
        />
      </div>
      <nav class="space-y-0.5">
        <NuxtLink
          v-for="item in primaryNav"
          :key="item.to"
          :to="item.to"
          :aria-current="isActive(item.to) ? 'page' : undefined"
          class="flex items-center gap-3 rounded-md px-2.5 py-2 text-sm transition-colors"
          :class="
            isActive(item.to)
              ? 'bg-primary/10 text-primary'
              : 'text-muted hover:bg-elevated hover:text-highlighted'
          "
          @click="app.closeMobileNav()"
        >
          <UIcon :name="item.icon" class="h-4 w-4 shrink-0" aria-hidden="true" />
          <span class="truncate">{{ item.label }}</span>
        </NuxtLink>
      </nav>
    </aside>
  </div>
</template>
