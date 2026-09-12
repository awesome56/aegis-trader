import type { Numeric } from '~/types/api'

/** Safely coerce backend numeric values (string | number) to a JS number. */
export function toNumber(value: Numeric | null | undefined, fallback = 0): number {
  if (value === null || value === undefined) return fallback
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function isNumeric(value: unknown): value is Numeric {
  if (typeof value === 'number') return Number.isFinite(value)
  if (typeof value === 'string' && value.trim() !== '') return Number.isFinite(Number(value))
  return false
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

export function round(value: number, decimals = 2): number {
  const factor = 10 ** decimals
  return Math.round(value * factor) / factor
}

/** 1234567 -> "1.23M". Used for volume/large counts. */
export function formatCompactNumber(
  value: Numeric | null | undefined,
  options: { decimals?: number } = {},
): string {
  const numeric = toNumber(value)
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: options.decimals ?? 2,
  }).format(numeric)
}

/** Quantities are shown with up to 4 significant decimals, trailing zeros trimmed. */
export function formatQuantity(value: Numeric | null | undefined): string {
  const numeric = toNumber(value)
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 4,
    minimumFractionDigits: 0,
  }).format(numeric)
}

export function formatNumber(value: Numeric | null | undefined, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(toNumber(value))
}
