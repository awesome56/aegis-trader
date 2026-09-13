<script setup lang="ts">
export interface AuditStage {
  key: string
  label: string
  status: 'done' | 'active' | 'pending' | 'failed'
  at?: string | null
  detail?: string | null
}

const props = defineProps<{ stages: AuditStage[] }>()

const dotClass: Record<AuditStage['status'], string> = {
  done: 'bg-emerald-400',
  active: 'bg-sky-400 animate-pulse',
  pending: 'bg-elevated ring-1 ring-default',
  failed: 'bg-rose-500',
}

const labelClass: Record<AuditStage['status'], string> = {
  done: 'text-default',
  active: 'text-highlighted',
  pending: 'text-dimmed',
  failed: 'text-down',
}
</script>

<template>
  <ol class="relative space-y-4">
    <li v-for="(stage, index) in props.stages" :key="stage.key" class="relative pl-6">
      <span
        v-if="index < props.stages.length - 1"
        class="absolute left-[5px] top-3 h-full w-px bg-default"
        aria-hidden="true"
      />
      <span
        class="absolute left-0 top-1.5 h-2.5 w-2.5 rounded-full"
        :class="dotClass[stage.status]"
        aria-hidden="true"
      />
      <p class="text-xs font-medium" :class="labelClass[stage.status]">{{ stage.label }}</p>
      <p v-if="stage.at" class="mt-0.5 text-[11px] text-muted">{{ stage.at }}</p>
      <p v-if="stage.detail" class="mt-0.5 text-[11px] text-muted">{{ stage.detail }}</p>
    </li>
  </ol>
</template>
