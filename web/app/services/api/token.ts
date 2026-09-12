/**
 * In-memory token holder.
 *
 * Access tokens live in memory only. The refresh token is persisted by the auth
 * store (cookie). This module is the single source the API client reads from,
 * which avoids coupling the client to Pinia.
 */

let accessToken: string | null = null
let refreshToken: string | null = null

export function setTokens(tokens: { accessToken: string; refreshToken: string }): void {
  accessToken = tokens.accessToken
  refreshToken = tokens.refreshToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function setRefreshToken(token: string | null): void {
  refreshToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

export function getRefreshToken(): string | null {
  return refreshToken
}

export function clearTokens(): void {
  accessToken = null
  refreshToken = null
}

export function hasTokens(): boolean {
  return Boolean(accessToken)
}
