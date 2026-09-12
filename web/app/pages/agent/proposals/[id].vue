<script setup lang="ts">
const route = useRoute()
const proposalId = computed(() => String(route.params.id ?? ''))
useHead({ title: () => `Proposal ${proposalId.value}` })
</script>

<template>
  <div>
    <PageHeader
      :title="`Proposal ${proposalId}`"
      subtitle="Strategy signals → Agent decision → Proposal → Risk → Order → Execution."
      eyebrow="Decision pipeline"
    />
    <FeaturePlaceholder
      title="Decision pipeline"
      phase="Phase 5"
      icon="i-lucide-git-branch"
      description="An expandable timeline of each pipeline stage with inspectable evidence. The Risk Engine verdict always visually overrides the agent recommendation."
    />
  </div>
</template>
