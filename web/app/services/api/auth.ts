import type {
  AuthResponse,
  AuthTokens,
  AuthUser,
  LoginPayload,
  RegisterPayload,
  SessionInfo,
} from '~/types/auth'
import type { MessageResponse } from '~/types/api'
import { api } from './client'

/**
 * Auth endpoints — IMPLEMENTED by the backend.
 * The only fully backed domain in Phase 1 besides system status.
 */
export const authService = {
  registrationOpen: () => api.get<{ open: boolean }>('/auth/registration-open'),
  login: (payload: LoginPayload) => api.post<AuthResponse>('/auth/login', payload),
  register: (payload: RegisterPayload) => api.post<AuthResponse>('/auth/register', payload),
  refresh: (refreshToken: string) =>
    api.post<AuthTokens>('/auth/refresh', { refresh_token: refreshToken }),
  logout: (refreshToken: string) =>
    api.post<MessageResponse>('/auth/logout', { refresh_token: refreshToken }),
  me: () => api.get<AuthUser>('/auth/me'),
  sessions: () => api.get<SessionInfo[]>('/auth/sessions'),
}
