import type { ISODateString, Numeric } from '~/types/api'

export function num(value: Numeric | null | undefined, fallback: Numeric = 0): Numeric {
  return value ?? fallback
}

export function numOrNull(value: Numeric | null | undefined): Numeric | null {
  return value ?? null
}

export function int(value: Numeric | null | undefined, fallback = 0): number {
  if (value === null || value === undefined) return fallback
  const parsed = Number(value)
  return Number.isFinite(parsed) ? Math.trunc(parsed) : fallback
}

export function iso(value: string | null | undefined, fallback?: string): ISODateString {
  return value ?? fallback ?? new Date().toISOString()
}

export function isoOrNull(value: string | null | undefined): ISODateString | null {
  return value ?? null
}

export function secondsBetween(start: string | null, end: string | null): number | null {
  if (!start || !end) return null
  const elapsed = Math.floor((Date.parse(end) - Date.parse(start)) / 1000)
  return Number.isFinite(elapsed) && elapsed >= 0 ? elapsed : null
}

export type Environment = 'DEMO' | 'LIVE'

/** Derive an account environment (DEMO/LIVE) from structured event payload metadata. */
export function normalizeEnvironment(
  payload: Record<string, unknown> | null | undefined,
): Environment | null {
  const raw = payload?.environment ?? payload?.account_environment
  return raw === 'DEMO' || raw === 'LIVE' ? raw : null
}
