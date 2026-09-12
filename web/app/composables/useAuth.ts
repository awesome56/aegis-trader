import { storeToRefs } from 'pinia'
import { useAuthStore } from '~/stores/auth'
import type { LoginPayload, RegisterPayload } from '~/types/auth'

/** Reactive auth state plus session actions. */
export function useAuth() {
  const store = useAuthStore()
  const { status, user, error, busy, isAuthenticated } = storeToRefs(store)

  return {
    status,
    user,
    error,
    busy,
    isAuthenticated,
    login: (payload: LoginPayload) => store.login(payload),
    register: (payload: RegisterPayload) => store.register(payload),
    logout: () => store.logout(),
    restore: () => store.restore(),
  }
}
