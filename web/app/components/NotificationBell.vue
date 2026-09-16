<script setup lang="ts">
import { onClickOutside } from '@vueuse/core'
import { useNotifications } from '~/composables/useNotifications'
import { formatRelative } from '~/utils/dates'
import type { NotificationSeverity } from '~/types/notifications'

const { items, unreadCount, markRead, markAllRead, listQuery } = useNotifications()

const open = ref(false)
const panelRef = ref<HTMLElement | null>(null)
onClickOutside(panelRef, () => {
  open.value = false
})

const tone: Record<NotificationSeverity, 'info' | 'warning' | 'danger'> = {
  INFO: 'info',
  WARNING: 'warning',
  CRITICAL: 'danger',
}

function onSelect(id: string): void {
  open.value = false
  if (unreadCount.value > 0) void markRead.mutateAsync(id).catch(() => undefined)
}
</script>

<template>
  <div ref="panelRef" class="relative">
    <UButton
      color="neutral"
      variant="ghost"
      size="sm"
      icon="i-lucide-bell"
      :aria-label="`Notifications (${unreadCount} unread)`"
      :aria-expanded="open"
      @click="open = !open"
    >
      <template #trailing>
        <span
          v-if="unreadCount > 0"
          class="ml-1 rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-semibold text-inverted"
        >
          {{ unreadCount > 99 ? '99+' : unreadCount }}
        </span>
      </template>
    </UButton>

    <div
      v-if="open"
      class="absolute right-0 z-40 mt-1 w-80 rounded-lg border border-default bg-default shadow-xl"
      role="dialog"
      aria-label="Notifications"
    >
      <div class="flex items-center justify-between border-b border-default px-3 py-2">
        <p class="text-xs font-semibold text-highlighted">Notifications</p>
        <button
          type="button"
          class="text-[11px] text-muted hover:text-highlighted disabled:opacity-50"
          :disabled="unreadCount === 0 || markAllRead.isPending.value"
          @click="markAllRead.mutate()"
        >
          Mark all read
        </button>
      </div>

      <div class="max-h-96 overflow-y-auto">
        <LoadingSkeleton v-if="listQuery.isLoading.value" class="p-3" :rows="3" />
        <ErrorState
          v-else-if="listQuery.isError.value"
          class="p-3"
          title="Notifications unavailable"
          message="The backend did not return notifications."
          @retry="listQuery.refetch()"
        />
        <ul v-else-if="items.length">
          <li v-for="item in items" :key="item.id" class="border-b border-default last:border-b-0">
            <component
              :is="item.link ? 'NuxtLink' : 'div'"
              :to="item.link"
              class="block px-3 py-2 transition-colors hover:bg-elevated/40"
              @click="onSelect(item.id)"
            >
              <div class="flex items-start justify-between gap-2">
                <p class="text-xs font-medium" :class="item.is_read ? 'text-muted' : 'text-highlighted'">
                  {{ item.title }}
                </p>
                <span
                  v-if="!item.is_read"
                  class="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
                  aria-label="Unread"
                />
              </div>
              <p class="mt-0.5 text-[11px] text-muted">{{ item.message }}</p>
              <div class="mt-1 flex items-center gap-2">
                <StatusBadge :label="item.category" :tone="tone[item.severity]" />
                <EnvironmentBadge :environment="item.environment" />
                <span class="text-[10px] text-dimmed">{{ formatRelative(item.created_at) }}</span>
              </div>
            </component>
          </li>
        </ul>
        <EmptyState v-else title="No notifications" icon="i-lucide-bell-off" />
      </div>

      <div class="border-t border-default px-3 py-2 text-center">
        <NuxtLink to="/activity" class="text-[11px] text-muted hover:text-highlighted" @click="open = false">
          View activity audit →
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
