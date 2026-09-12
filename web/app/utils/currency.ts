import type { Numeric } from '~/types/api'
import { toNumber } from './numbers'

export interface CurrencyOptions {
  currency?: string
  decimals?: number
  compact?: boolean
  showSign?: boolean
  currencyDisplay?: 'symbol' | 'code'
}

/** Central currency formatter. Supports multiple currencies for future use. */
export function formatCurrency(
  value: Numeric | null | undefined,
  options: CurrencyOptions = {},
): string {
  const {
    currency = 'USD',
    decimals = 2,
    compact = false,
    showSign = false,
    currencyDisplay = 'symbol',
  } = options

  const numeric = toNumber(value)
  const formatted = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    currencyDisplay,
    notation: compact ? 'compact' : 'standard',
    minimumFractionDigits: compact ? 0 : decimals,
    maximumFractionDigits: decimals,
  }).format(Math.abs(numeric))

  if (numeric < 0) return `-${formatted}`
  if (showSign && numeric > 0) return `+${formatted}`
  return formatted
}

/** Price formatter with adaptive decimals (pennies vs large-cap equities). */
export function formatPrice(value: Numeric | null | undefined, decimals?: number): string {
  const numeric = toNumber(value)
  const resolved =
    decimals ?? (Math.abs(numeric) >= 1000 ? 2 : Math.abs(numeric) >= 1 ? 2 : 4)
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: resolved,
    maximumFractionDigits: resolved,
  }).format(numeric)
}
