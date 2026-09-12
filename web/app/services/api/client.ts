import type { ApiErrorShape } from '~/types/api'
import { apiConfig } from './config'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './token'

/** Normalised API error thrown by every service call. */
export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details?: Record<string, unknown>

  constructor(shape: ApiErrorShape) {
    super(shape.message)
    this.name = 'ApiError'
    this.code = shape.code
    this.status = shape.status
    this.details = shape.details
  }
}

export interface RequestOptions {
  query?: Record<string, unknown>
  body?: unknown
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  signal?: AbortSignal
  timeout?: number
}

interface RefreshResponse {
  access_token: string
  refresh_token: string
}

function endpoint(path: string): string {
  const { apiPrefix } = apiConfig()
  return path.startsWith('/') ? `${apiPrefix}${path}` : `${apiPrefix}/${path}`
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  // ofetch / $fetch errors expose `statusCode`/`response`/`data`.
  if (isRecord(error)) {
    const status =
      typeof error.statusCode === 'number'
        ? error.statusCode
        : typeof error.status === 'number'
          ? error.status
          : 0
    const data = isRecord(error.data) ? error.data : undefined
    const envelope = data && isRecord(data.error) ? data.error : undefined

    if (envelope) {
      return new ApiError({
        status,
        code: typeof envelope.code === 'string' ? envelope.code : 'api_error',
        message:
          typeof envelope.message === 'string' ? envelope.message : 'Request failed',
        details: isRecord(envelope.details)
          ? (envelope.details as Record<string, unknown>)
          : undefined,
      })
    }

    if (status === 0) {
      return new ApiError({
        status: 0,
        code: 'network_error',
        message: 'Cannot reach the Aegis backend',
      })
    }
  }

  return new ApiError({
    status: 0,
    code: 'unknown_error',
    message: error instanceof Error ? error.message : 'Unexpected error',
  })
}

let refreshPromise: Promise<boolean> | null = null

async function performRefresh(): Promise<boolean> {
  const token = getRefreshToken()
  if (!token) return false
  try {
    const response = await $fetch<RefreshResponse>(endpoint('/auth/refresh'), {
      baseURL: apiConfig().baseUrl,
      method: 'POST',
      body: { refresh_token: token },
    })
    setTokens({
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
    })
    return true
  } catch {
    clearTokens()
    return false
  }
}

/** Single-flight refresh so concurrent 401s trigger only one refresh. */
function refreshTokens(): Promise<boolean> {
  if (refreshPromise) return refreshPromise
  const promise = performRefresh().finally(() => {
    refreshPromise = null
  })
  refreshPromise = promise
  return promise
}

async function execute<T>(
  path: string,
  options: RequestOptions,
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`

  return await $fetch<T>(endpoint(path), {
    baseURL: apiConfig().baseUrl,
    method: options.method ?? 'GET',
    query: options.query,
    body: options.body as Record<string, unknown> | undefined,
    headers,
    signal: options.signal,
    timeout: options.timeout ?? 20_000,
  })
}

/**
 * Central authenticated request helper.
 *
 * Responsibilities: base URL, auth header, refresh-and-retry on 401, error
 * normalisation, timeouts and cancellation. No other module builds URLs or
 * manages tokens.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  try {
    return await execute<T>(path, options)
  } catch (error) {
    const normalized = normalizeError(error)
    if (normalized.status === 401 && getRefreshToken()) {
      const refreshed = await refreshTokens()
      if (refreshed) {
        try {
          return await execute<T>(path, options)
        } catch (retryError) {
          throw normalizeError(retryError)
        }
      }
    }
    throw normalized
  }
}

export const api = {
  get: <T>(path: string, options: Omit<RequestOptions, 'method' | 'body'> = {}) =>
    apiRequest<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options: Omit<RequestOptions, 'method' | 'body'> = {}) =>
    apiRequest<T>(path, { ...options, method: 'POST', body }),
  put: <T>(path: string, body?: unknown, options: Omit<RequestOptions, 'method' | 'body'> = {}) =>
    apiRequest<T>(path, { ...options, method: 'PUT', body }),
  delete: <T>(path: string, options: Omit<RequestOptions, 'method' | 'body'> = {}) =>
    apiRequest<T>(path, { ...options, method: 'DELETE' }),
}
