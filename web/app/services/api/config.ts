/**
 * Runtime API configuration.
 *
 * Nuxt's `runtimeConfig` is only available inside the Nuxt app context, so a
 * startup plugin copies the public values here. Services read from this module
 * instead of calling `useRuntimeConfig()` deep in async query functions.
 */

export interface ApiRuntimeConfig {
  baseUrl: string
  wsUrl: string
  useMock: boolean
  apiPrefix: string
  appName: string
  appVersion: string
}

const DEFAULTS: ApiRuntimeConfig = {
  baseUrl: 'http://localhost:8000',
  wsUrl: 'ws://localhost:8000',
  useMock: false,
  apiPrefix: '/api/v1',
  appName: 'Aegis Trader',
  appVersion: '0.1.0',
}

let current: ApiRuntimeConfig = { ...DEFAULTS }

export function configureApi(next: Partial<ApiRuntimeConfig>): void {
  current = { ...current, ...next }
}

export function apiConfig(): Readonly<ApiRuntimeConfig> {
  return current
}

export function isMockEnabled(): boolean {
  return current.useMock
}

export function resetApiConfig(): void {
  current = { ...DEFAULTS }
}
