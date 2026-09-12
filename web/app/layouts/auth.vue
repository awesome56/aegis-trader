<template>
  <div class="flex min-h-screen flex-col bg-default">
    <div class="flex flex-1 items-center justify-center px-4 py-10">
      <div class="w-full max-w-md">
        <div class="mb-6 flex items-center justify-center gap-2">
          <span
            class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 text-primary"
            aria-hidden="true"
          >
            <UIcon name="i-lucide-activity" class="h-5 w-5" />
          </span>
          <span class="text-lg font-semibold tracking-tight text-highlighted">Aegis Trader</span>
        </div>
        <slot />
        <p class="mt-6 text-center text-[11px] text-muted">
          Paper trading environment · Not financial advice
        </p>
      </div>
    </div>
  </div>
</template>
