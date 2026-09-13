<script setup lang="ts">
import type { RiskEvaluation } from '~/types/agent'
import { formatCurrency } from '~/utils/currency'
import { formatDateTime } from '~/utils/dates'
import { formatPercentage } from '~/utils/percentage'

const props = defineProps<{ evaluation: RiskEvaluation }>()

const expanded = ref<Record<string, boolean>>({})
function toggle(key: string): void {
  expanded.value = { ...expanded.value, [key]: !expanded.value[key] }
}

const decisionTone = computed(() =>
  props.evaluation.decision === 'APPROVED' || props.evaluation.decision === 'APPROVED_WITH_WARNINGS'
    ? ('success' as const)
    : ('danger' as const),
)

const metrics = computed(() => {
  const e = props.evaluation
  return [
    { label: 'Requested quantity', value: String(e.requested_quantity) },
    { label: 'Approved quantity', value: e.approved_quantity === null ? '—' : String(e.approved_quantity) },
    { label: 'Requested notional', value: formatCurrency(e.requested_notional, { currency: 'USD' }) },
    { label: 'Approved notional', value: e.approved_notional === null ? '—' : formatCurrency(e.approved_notional, { currency: 'USD' }) },
    { label: 'Estimated risk', value: e.estimated_risk_amount === null ? '—' : formatCurrency(e.estimated_risk_amount, { currency: 'USD' }) },
    { label: 'Reward / risk', value: e.risk_reward_ratio === null ? '—' : String(e.risk_reward_ratio) },
    { label: 'Exposure before', value: formatPercentage(e.portfolio_exposure_before_percent) },
    { label: 'Exposure after', value: e.portfolio_exposure_after_percent === null ? '—' : formatPercentage(e.portfolio_exposure_after_percent) },
  ]
})

const failedRules = computed(() => props.evaluation.rules.filter((rule) => !rule.passed))
</script>

<template>
  <div class="rounded-lg border border-default bg-elevated/30 p-4">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold text-highlighted">Risk evaluation</h3>
      <StatusBadge :label="evaluation.decision.replaceAll('_', ' ')" :tone="decisionTone" dot />
    </div>
    <p class="mt-1 text-[11px] text-muted">
      {{ formatDateTime(evaluation.evaluated_at) }} · score {{ evaluation.risk_score }}
    </p>

    <div class="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
      <div v-for="metric in metrics" :key="metric.label">
        <p class="text-[11px] uppercase tracking-wide text-muted">{{ metric.label }}</p>
        <p class="num mt-0.5 text-sm text-default">{{ metric.value }}</p>
      </div>
    </div>

    <div v-if="failedRules.length" class="mt-4">
      <p class="text-xs font-medium text-down">Failed rules</p>
      <ul class="mt-1 space-y-1">
        <li v-for="rule in failedRules" :key="rule.key" class="text-xs text-default">
          {{ rule.message }}
        </li>
      </ul>
    </div>
    <div v-if="evaluation.warnings.length" class="mt-3">
      <p class="text-xs font-medium text-amber-400">Warnings</p>
      <ul class="mt-1 space-y-1">
        <li v-for="(warning, index) in evaluation.warnings" :key="index" class="text-xs text-muted">
          {{ warning }}
        </li>
      </ul>
    </div>
    <div v-if="evaluation.reasons.length" class="mt-3">
      <p class="text-xs font-medium text-muted">Reasons</p>
      <ul class="mt-1 space-y-1">
        <li v-for="(reason, index) in evaluation.reasons" :key="index" class="text-xs text-muted">
          {{ reason }}
        </li>
      </ul>
    </div>

    <div v-if="evaluation.rules.length" class="mt-4">
      <p class="text-xs font-medium text-muted">Rule results ({{ evaluation.rules.length }})</p>
      <ul class="mt-2 divide-y divide-default">
        <li v-for="rule in evaluation.rules" :key="rule.key">
          <button
            type="button"
            class="flex w-full items-center justify-between gap-2 py-2 text-left"
            @click="toggle(rule.key)"
          >
            <span class="flex items-center gap-2 text-xs text-default">
              <span
                class="inline-block h-1.5 w-1.5 rounded-full"
                :class="rule.passed ? 'bg-emerald-400' : 'bg-rose-500'"
                aria-hidden="true"
              />
              {{ rule.key }}
            </span>
            <span class="num text-[11px] text-muted">
              {{ rule.current ?? '—' }} / {{ rule.limit ?? '—' }}
              <UIcon
                :name="expanded[rule.key] ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
                class="ml-1 inline h-3.5 w-3.5"
              />
            </span>
          </button>
          <div v-if="expanded[rule.key]" class="pb-2 pl-4 text-[11px] text-muted">
            <p>{{ rule.message }}</p>
            <p class="mt-0.5">
              severity {{ rule.severity }}
              <span v-if="rule.utilization_percent !== null"> · utilization {{ formatPercentage(rule.utilization_percent) }}</span>
            </p>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>
