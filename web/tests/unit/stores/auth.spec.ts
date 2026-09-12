import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getAccessToken } from '~/services/api/token'
import { useAuthStore } from '~/stores/auth'

const { loginMock, registerMock, meMock, logoutMock } = vi.hoisted(() => ({
  loginMock: vi.fn(),
  registerMock: vi.fn(),
  meMock: vi.fn(),
  logoutMock: vi.fn(),
}))

vi.mock('~/services/api/auth', () => ({
  authService: {
    login: loginMock,
    register: registerMock,
    me: meMock,
    logout: logoutMock,
  },
}))

vi.mock('~/stores/websocket', () => ({
  useWebSocketStore: () => ({ connect: vi.fn(), disconnect: vi.fn() }),
}))

const session = {
  user: {
    id: 'u1',
    email: 'owner@example.com',
    full_name: null,
    is_active: true,
    is_superuser: true,
    created_at: '2026-01-01T00:00:00.000Z',
    last_login_at: null,
  },
  tokens: {
    access_token: 'access-1',
    refresh_token: 'refresh-1',
    token_type: 'bearer',
    expires_in: 0,
  },
}

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('starts in the unknown state', () => {
    expect(useAuthStore().status).toBe('unknown')
  })

  it('login stores the session and tokens', async () => {
    loginMock.mockResolvedValue(session)
    const store = useAuthStore()

    const ok = await store.login({ email: 'owner@example.com', password: 'x' })

    expect(ok).toBe(true)
    expect(store.status).toBe('authenticated')
    expect(store.user?.email).toBe('owner@example.com')
    expect(getAccessToken()).toBe('access-1')
  })

  it('login failure surfaces an error and stays unauthenticated', async () => {
    loginMock.mockRejectedValue(new Error('Invalid email or password'))
    const store = useAuthStore()

    const ok = await store.login({ email: 'owner@example.com', password: 'bad' })

    expect(ok).toBe(false)
    expect(store.status).toBe('unauthenticated')
    expect(store.error).toContain('Invalid email or password')
  })

  it('logout clears the session', async () => {
    loginMock.mockResolvedValue(session)
    logoutMock.mockResolvedValue({ detail: 'ok' })
    const store = useAuthStore()
    await store.login({ email: 'owner@example.com', password: 'x' })

    await store.logout()

    expect(store.status).toBe('unauthenticated')
    expect(store.user).toBeNull()
    expect(getAccessToken()).toBeNull()
  })
})
