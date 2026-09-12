<script setup lang="ts">
import { z } from 'zod'
import { useAuth } from '~/composables/useAuth'
import { useApi } from '~/composables/useApi'

definePageMeta({ public: true, layout: 'auth' })
useHead({ title: 'Sign in' })

const route = useRoute()
const router = useRouter()
const { login, register, busy, error } = useAuth()
const { auth: authService } = useApi()

const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const fullName = ref('')
const fieldErrors = ref<Record<string, string>>({})

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})

const registerSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(12, 'Password must be at least 12 characters'),
  fullName: z.string().optional(),
})

onMounted(async () => {
  try {
    const { open } = await authService.registrationOpen()
    if (open) mode.value = 'register'
  } catch {
    // Backend unreachable; default to sign-in.
  }
})

function validate(): boolean {
  fieldErrors.value = {}
  const schema = mode.value === 'login' ? loginSchema : registerSchema
  const result = schema.safeParse({
    email: email.value,
    password: password.value,
    fullName: fullName.value,
  })
  if (result.success) return true
  const errors: Record<string, string> = {}
  for (const issue of result.error.issues) {
    const key = String(issue.path[0] ?? 'form')
    if (!errors[key]) errors[key] = issue.message
  }
  fieldErrors.value = errors
  return false
}

async function submit(): Promise<void> {
  if (!validate()) return
  const ok =
    mode.value === 'login'
      ? await login({ email: email.value, password: password.value })
      : await register({
          email: email.value,
          password: password.value,
          full_name: fullName.value || undefined,
        })
  if (ok) {
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    await router.push(redirect)
  }
}
</script>

<template>
  <div class="rounded-xl border border-default bg-elevated/20 p-6">
    <h1 class="text-base font-semibold text-highlighted">
      {{ mode === 'login' ? 'Sign in' : 'Create owner account' }}
    </h1>
    <p class="mt-1 text-xs text-muted">
      {{
        mode === 'login'
          ? 'Authenticate to access the trading terminal.'
          : 'Bootstrap registration is only available before the first account exists.'
      }}
    </p>

    <form class="mt-5 space-y-3" novalidate @submit.prevent="submit">
      <div v-if="mode === 'register'">
        <label for="fullName" class="text-[11px] font-medium uppercase tracking-wide text-muted">
          Full name
        </label>
        <input
          id="fullName"
          v-model="fullName"
          type="text"
          autocomplete="name"
          class="mt-1 w-full rounded-md border border-default bg-elevated/40 px-3 py-2 text-sm text-highlighted outline-none focus:ring-2 focus:ring-primary/50"
        />
      </div>

      <div>
        <label for="email" class="text-[11px] font-medium uppercase tracking-wide text-muted">
          Email
        </label>
        <input
          id="email"
          v-model="email"
          type="email"
          autocomplete="email"
          class="mt-1 w-full rounded-md border bg-elevated/40 px-3 py-2 text-sm text-highlighted outline-none focus:ring-2 focus:ring-primary/50"
          :class="fieldErrors.email ? 'border-danger' : 'border-default'"
          :aria-invalid="Boolean(fieldErrors.email)"
          aria-describedby="email-error"
        />
        <p v-if="fieldErrors.email" id="email-error" class="mt-1 text-[11px] text-danger">
          {{ fieldErrors.email }}
        </p>
      </div>

      <div>
        <label for="password" class="text-[11px] font-medium uppercase tracking-wide text-muted">
          Password
        </label>
        <input
          id="password"
          v-model="password"
          type="password"
          :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
          class="mt-1 w-full rounded-md border bg-elevated/40 px-3 py-2 text-sm text-highlighted outline-none focus:ring-2 focus:ring-primary/50"
          :class="fieldErrors.password ? 'border-danger' : 'border-default'"
          :aria-invalid="Boolean(fieldErrors.password)"
          aria-describedby="password-error"
        />
        <p v-if="fieldErrors.password" id="password-error" class="mt-1 text-[11px] text-danger">
          {{ fieldErrors.password }}
        </p>
      </div>

      <p v-if="error" class="rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger" role="alert">
        {{ error }}
      </p>

      <UButton type="submit" block :loading="busy" :disabled="busy">
        {{ mode === 'login' ? 'Sign in' : 'Create account' }}
      </UButton>

      <UButton
        color="neutral"
        variant="ghost"
        size="sm"
        block
        :disabled="busy"
        @click="mode = mode === 'login' ? 'register' : 'login'"
      >
        {{ mode === 'login' ? 'First run? Create the owner account' : 'I already have an account' }}
      </UButton>
    </form>
  </div>
</template>
