import { defineStore } from 'pinia'
import type { AuthResponse, AuthStatus, AuthUser, LoginPayload, RegisterPayload } from '~/types/auth'
import { authService } from '~/services/api/auth'
import {
  clearTokens,
  getRefreshToken,
  setRefreshToken,
  setTokens,
} from '~/services/api/token'
import { useWebSocketStore } from './websocket'

/**
 * Authentication/session state.
 *
 * Access token: in memory only. Refresh token: persisted in a SameSite=Strict
 * cookie (HttpOnly cookies require backend support — see the completion report).
 */
export const useAuthStore = defineStore('auth', () => {
  const refreshCookie = useCookie<string | null>('aegis.refresh_token', {
    sameSite: 'strict',
    secure: !import.meta.dev,
    maxAge: 60 * 60 * 24 * 14,
    path: '/',
  })

  const status = ref<AuthStatus>('unknown')
  const user = ref<AuthUser | null>(null)
  const error = ref<string | null>(null)
  const busy = ref(false)

  const isAuthenticated = computed(() => status.value === 'authenticated')

  function applySession(response: AuthResponse): void {
    setTokens({
      accessToken: response.tokens.access_token,
      refreshToken: response.tokens.refresh_token,
    })
    refreshCookie.value = response.tokens.refresh_token
    user.value = response.user
    status.value = 'authenticated'
    error.value = null
    useWebSocketStore().connect(response.tokens.access_token)
  }

  /** Restore a session from the persisted refresh token on app start. */
  let restorePromise: Promise<void> | null = null

  async function restore(): Promise<void> {
    if (status.value !== 'unknown') return
    if (restorePromise) return restorePromise
    restorePromise = doRestore().finally(() => {
      restorePromise = null
    })
    return restorePromise
  }

  async function doRestore(): Promise<void> {
    const stored = refreshCookie.value
    if (!stored) {
      status.value = 'unauthenticated'
      return
    }
    // Seed the refresh token so the client's 401-retry can mint an access token.
    setRefreshToken(stored)
    try {
      const currentUser = await authService.me()
      user.value = currentUser
      status.value = 'authenticated'
      useWebSocketStore().connect()
    } catch {
      clearTokens()
      refreshCookie.value = null
      user.value = null
      status.value = 'unauthenticated'
    }
  }

  async function login(payload: LoginPayload): Promise<boolean> {
    busy.value = true
    error.value = null
    try {
      applySession(await authService.login(payload))
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Sign in failed'
      status.value = 'unauthenticated'
      return false
    } finally {
      busy.value = false
    }
  }

  async function register(payload: RegisterPayload): Promise<boolean> {
    busy.value = true
    error.value = null
    try {
      applySession(await authService.register(payload))
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Registration failed'
      status.value = 'unauthenticated'
      return false
    } finally {
      busy.value = false
    }
  }

  async function logout(): Promise<void> {
    const token = getRefreshToken()
    if (token) {
      try {
        await authService.logout(token)
      } catch {
        // Best-effort revocation; always clear locally.
      }
    }
    clearTokens()
    refreshCookie.value = null
    user.value = null
    status.value = 'unauthenticated'
    useWebSocketStore().disconnect()
  }

  return {
    status,
    user,
    error,
    busy,
    isAuthenticated,
    restore,
    login,
    register,
    logout,
  }
})
