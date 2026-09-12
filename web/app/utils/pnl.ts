import type { Numeric } from '~/types/api'
import { formatCurrency } from './currency'
import { toNumber } from './numbers'

export type PnlTone = 'up' | 'down' | 'flat'

const EPSILON = 1e-9

/** Direction of a value, used for semantic (color + sign) treatment. */
export function pnlTone(value: Numeric | null | undefined): PnlTone {
  const numeric = toNumber(value)
  if (Math.abs(numeric) < EPSILON) return 'flat'
  return numeric > 0 ? 'up' : 'down'
}

/** Explicit sign prefix so meaning never depends on color alone. */
export function pnlSign(value: Numeric | null | undefined): '+' | '-' | '' {
  const tone = pnlTone(value)
  if (tone === 'up') return '+'
  if (tone === 'down') return '-'
  return ''
}

/** Signed currency P&L, e.g. "+$1,842.35". */
export function formatPnL(value: Numeric | null | undefined, currency = 'USD'): string {
  return formatCurrency(value, { currency, showSign: true })
}

/** Tailwind text-color class for a P&L tone. */
export function pnlColorClass(value: Numeric | null | undefined): string {
  switch (pnlTone(value)) {
    case 'up':
      return 'text-up'
    case 'down':
      return 'text-down'
    default:
      return 'text-flat'
  }
}
