<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value?: string | null
    delta?: string | null
    deltaTone?: 'up' | 'down' | 'flat'
    hint?: string | null
    loading?: boolean
  }>(),
  {
    value: null,
    delta: null,
    deltaTone: 'flat',
    hint: null,
    loading: false,
  },
)

const toneClass: Record<'up' | 'down' | 'flat', string> = {
  up: 'text-up',
  down: 'text-down',
  flat: 'text-flat',
}
</script>

<template>
  <div
    class="rounded-lg border border-default bg-elevated/30 px-3 py-2.5 transition-colors hover:border-accented"
  >
    <div class="flex items-center justify-between gap-2">
      <span class="text-[11px] font-medium uppercase tracking-wide text-muted">{{ label }}</span>
      <slot name="icon" />
    </div>

    <div v-if="loading" class="mt-2 h-6 w-24 animate-pulse rounded bg-elevated" />
    <div v-else class="mt-1 flex items-baseline gap-2">
      <span class="num text-lg font-semibold leading-tight text-highlighted">{{ value ?? '—' }}</span>
      <span v-if="delta" class="num text-xs font-medium" :class="toneClass[deltaTone]">
        {{ delta }}
      </span>
    </div>

    <p v-if="hint" class="mt-0.5 truncate text-[11px] text-muted">{{ hint }}</p>
  </div>
</template>
