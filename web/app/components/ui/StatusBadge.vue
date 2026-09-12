<script setup lang="ts">
export type BadgeTone =
  | 'neutral'
  | 'info'
  | 'success'
  | 'warning'
  | 'danger'
  | 'paper'
  | 'live'

const props = withDefaults(
  defineProps<{
    label: string
    tone?: BadgeTone
    dot?: boolean
    icon?: string
  }>(),
  { tone: 'neutral', dot: false, icon: undefined },
)

const toneClasses: Record<BadgeTone, string> = {
  neutral: 'bg-elevated text-muted ring-1 ring-inset ring-default',
  info: 'bg-sky-500/10 text-sky-400 ring-1 ring-inset ring-sky-500/30',
  success: 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/30',
  warning: 'bg-amber-500/10 text-amber-400 ring-1 ring-inset ring-amber-500/30',
  danger: 'bg-rose-500/10 text-rose-400 ring-1 ring-inset ring-rose-500/30',
  paper: 'bg-paper/10 text-paper ring-1 ring-inset ring-paper/30',
  live: 'bg-live/10 text-live ring-1 ring-inset ring-live/40',
}

const cls = computed(() => toneClasses[props.tone])
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
    :class="cls"
  >
    <span
      v-if="dot"
      class="h-1.5 w-1.5 shrink-0 rounded-full bg-current"
      aria-hidden="true"
    />
    <UIcon v-if="icon" :name="icon" class="h-3.5 w-3.5" aria-hidden="true" />
    {{ label }}
  </span>
</template>
