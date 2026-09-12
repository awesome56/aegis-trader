<script setup lang="ts">
import { onKeyStroke } from '@vueuse/core'

interface Props {
  open: boolean
  title: string
  description?: string
  consequences?: string[]
  confirmLabel?: string
  cancelLabel?: string
  tone?: 'default' | 'danger'
  /** When set, the user must type this exact phrase to enable confirmation. */
  confirmPhrase?: string
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  description: undefined,
  consequences: () => [],
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  tone: 'default',
  confirmPhrase: undefined,
  loading: false,
})

const emit = defineEmits<{
  'update:open': [boolean]
  confirm: []
  cancel: []
}>()

const titleId = useId()
const typed = ref('')
const confirmButton = ref<HTMLButtonElement | null>(null)

const canConfirm = computed(
  () => !props.confirmPhrase || typed.value.trim() === props.confirmPhrase,
)

const isDanger = computed(() => props.tone === 'danger')

watch(
  () => props.open,
  async (open) => {
    if (!open) return
    typed.value = ''
    await nextTick()
    focusConfirm()
  },
)

function focusConfirm(): void {
  const instance = confirmButton.value as unknown as { $el?: HTMLElement } | null
  instance?.$el?.focus?.()
}

function close(): void {
  if (props.loading) return
  emit('update:open', false)
  emit('cancel')
}

function confirm(): void {
  if (!canConfirm.value || props.loading) return
  emit('confirm')
}

onKeyStroke('Escape', () => {
  if (props.open) close()
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="presentation"
    >
      <div class="absolute inset-0 bg-black/60 backdrop-blur-[1px]" @click="close" />

      <div
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        class="relative z-10 w-full max-w-md rounded-xl border border-default bg-default p-5 shadow-2xl"
      >
        <div class="flex items-start gap-3">
          <UIcon
            :name="isDanger ? 'i-lucide-triangle-alert' : 'i-lucide-circle-help'"
            class="mt-0.5 h-5 w-5 shrink-0"
            :class="isDanger ? 'text-danger' : 'text-primary'"
            aria-hidden="true"
          />
          <div class="min-w-0 flex-1">
            <h2 :id="titleId" class="text-sm font-semibold text-highlighted">{{ title }}</h2>
            <p v-if="description" class="mt-1 text-xs text-muted">{{ description }}</p>

            <ul
              v-if="consequences.length"
              class="mt-3 list-disc space-y-1 rounded-md border border-default bg-elevated/40 py-2 pl-8 pr-3 text-xs text-muted"
            >
              <li v-for="item in consequences" :key="item">{{ item }}</li>
            </ul>

            <div v-if="confirmPhrase" class="mt-3">
              <label class="text-[11px] font-medium uppercase tracking-wide text-muted">
                Type <span class="font-mono text-highlighted">{{ confirmPhrase }}</span> to confirm
              </label>
              <input
                v-model="typed"
                type="text"
                class="mt-1 w-full rounded-md border border-default bg-elevated/40 px-2.5 py-1.5 text-sm text-highlighted outline-none focus:ring-2 focus:ring-primary/50"
                :aria-label="`Type ${confirmPhrase} to confirm`"
              />
            </div>
          </div>
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <UButton color="neutral" variant="ghost" size="sm" :disabled="loading" @click="close">
            {{ cancelLabel }}
          </UButton>
          <UButton
            ref="confirmButton"
            :color="isDanger ? 'error' : 'primary'"
            size="sm"
            :disabled="!canConfirm"
            :loading="loading"
            @click="confirm"
          >
            {{ confirmLabel }}
          </UButton>
        </div>
      </div>
    </div>
  </Teleport>
</template>
