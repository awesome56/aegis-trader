import type { Numeric } from '~/types/api'
import { toNumber } from './numbers'

export interface PercentOptions {
  decimals?: number
  showSign?: boolean
  /** When true the input is a fraction (0.0147) and is multiplied by 100. */
  asFraction?: boolean
}

/** Format a backend percentage value (already expressed in percent units). */
export function formatPercentage(
  value: Numeric | null | undefined,
  options: PercentOptions = {},
): string {
  const { decimals = 2, showSign = false, asFraction = false } = options
  const raw = toNumber(value)
  const numeric = asFraction ? raw * 100 : raw
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Math.abs(numeric))

  if (numeric < 0) return `-${formatted}%`
  if (showSign && numeric > 0) return `+${formatted}%`
  return `${formatted}%`
}

/** Percentage always carrying an explicit sign (for P&L/returns). */
export function formatSignedPercentage(
  value: Numeric | null | undefined,
  decimals = 2,
): string {
  return formatPercentage(value, { decimals, showSign: true })
}

/**
 * Format a ratio (0..1 or 0..100) as an exposure/usage bar label.
 * Values are clamped to 0..100 and rendered without a sign.
 */
export function formatUsage(value: Numeric | null | undefined, decimals = 1): string {
  const numeric = Math.max(0, Math.min(100, toNumber(value)))
  return `${numeric.toFixed(decimals)}%`
}
