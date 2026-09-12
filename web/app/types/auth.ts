import type { ISODateString } from './api'

/** Matches the backend `UserRead` schema. */
export interface AuthUser {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  created_at: ISODateString
  last_login_at: ISODateString | null
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

/** Matches `POST /auth/login` and `/auth/register` responses. */
export interface AuthResponse {
  user: AuthUser
  tokens: AuthTokens
}

export interface LoginPayload {
  email: string
  password: string
  device_name?: string
}

export interface RegisterPayload {
  email: string
  password: string
  full_name?: string
}

export interface SessionInfo {
  id: string
  device_name: string | null
  ip_address: string | null
  created_at: ISODateString
  last_used_at: ISODateString | null
  expires_at: ISODateString
}

export type AuthStatus = 'unknown' | 'unauthenticated' | 'authenticated'
