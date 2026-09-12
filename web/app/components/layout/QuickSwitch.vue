<script setup lang="ts">
import { onKeyStroke } from '@vueuse/core'
import { primaryNav } from '~/utils/navigation'
import { useAppStore } from '~/stores/app'

const app = useAppStore()
const router = useRouter()

const open = computed({
  get: () => app.commandPaletteOpen,
  set: (value: boolean) => {
    if (value) app.commandPaletteOpen = true
    else app.toggleCommandPalette()
  },
})

const query = ref('')
const input = ref<HTMLInputElement | null>(null)

const results = computed(() => {
  const term = query.value.trim().toLowerCase()
  if (!term) return primaryNav
  return primaryNav.filter((item) => item.label.toLowerCase().includes(term))
})

watch(open, async (isOpen) => {
  if (!isOpen) return
  query.value = ''
  await nextTick()
  input.value?.focus()
})

// Cmd/Ctrl + K
onKeyStroke('k', (event) => {
  if (!(event.metaKey || event.ctrlKey)) return
  event.preventDefault()
  app.toggleCommandPalette()
})

function go(to: string): void {
  void router.push(to)
  open.value = false
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') open.value = false
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-start justify-center p-4 pt-24">
      <div class="absolute inset-0 bg-black/60" @click="open = false" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Quick navigation"
        class="relative z-10 w-full max-w-lg overflow-hidden rounded-xl border border-default bg-default shadow-2xl"
        @keydown="onKeydown"
      >
        <div class="flex items-center gap-2 border-b border-default px-3 py-2">
          <UIcon name="i-lucide-search" class="h-4 w-4 text-muted" aria-hidden="true" />
          <input
            ref="input"
            v-model="query"
            type="text"
            placeholder="Jump to a page…"
            class="w-full bg-transparent text-sm text-highlighted outline-none placeholder:text-muted"
            aria-label="Search pages"
          />
          <kbd class="rounded border border-default px-1.5 py-0.5 text-[10px] text-muted">ESC</kbd>
        </div>
        <ul class="max-h-80 overflow-y-auto p-1">
          <li v-for="item in results" :key="item.to">
            <button
              type="button"
              class="flex w-full items-center gap-3 rounded-md px-2.5 py-2 text-left text-sm text-muted transition-colors hover:bg-elevated hover:text-highlighted"
              @click="go(item.to)"
            >
              <UIcon :name="item.icon" class="h-4 w-4 shrink-0" aria-hidden="true" />
              {{ item.label }}
            </button>
          </li>
          <li v-if="results.length === 0" class="px-3 py-6 text-center text-xs text-muted">
            No matching pages.
          </li>
        </ul>
      </div>
    </div>
  </Teleport>
</template>
