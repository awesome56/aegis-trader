import { describe, expect, it } from 'vitest'
import { formatCurrency, formatPrice } from '~/utils/currency'
import { formatPercentage, formatSignedPercentage, formatUsage } from '~/utils/percentage'
import { formatCompactNumber, formatQuantity, toNumber } from '~/utils/numbers'
import { formatDuration } from '~/utils/dates'
import { formatPnL, pnlSign, pnlTone } from '~/utils/pnl'

describe('toNumber', () => {
  it('coerces backend decimal strings', () => {
    expect(toNumber('1234.56')).toBe(1234.56)
    expect(toNumber(1234.56)).toBe(1234.56)
  })

  it('falls back for invalid values', () => {
    expect(toNumber(null)).toBe(0)
    expect(toNumber(undefined, -1)).toBe(-1)
    expect(toNumber('not-a-number', 5)).toBe(5)
  })
})

describe('currency formatting', () => {
  it('formats USD with a symbol', () => {
    expect(formatCurrency('127480.25')).toBe('$127,480.25')
  })

  it('formats negative values with a leading sign', () => {
    expect(formatCurrency('-1234.5')).toBe('-$1,234.50')
  })

  it('adds an explicit positive sign when requested', () => {
    expect(formatCurrency('1842.35', { showSign: true })).toBe('+$1,842.35')
  })

  it('formats prices with adaptive decimals', () => {
    expect(formatPrice('126.85')).toBe('126.85')
    expect(formatPrice('0.4721')).toBe('0.4721')
  })
})

describe('percentage formatting', () => {
  it('formats percent values (already in percent units)', () => {
    expect(formatPercentage('1.47')).toBe('1.47%')
    expect(formatPercentage('67.64')).toBe('67.64%')
  })

  it('formats signed percentages', () => {
    expect(formatSignedPercentage('1.47')).toBe('+1.47%')
    expect(formatSignedPercentage('-2.10')).toBe('-2.10%')
    expect(formatSignedPercentage('0')).toBe('0.00%')
  })

  it('treats fractions as fractions when asked', () => {
    expect(formatPercentage('0.0147', { asFraction: true })).toBe('1.47%')
  })

  it('clamps usage to 0..100', () => {
    expect(formatUsage('84.55')).toBe('84.5%')
    expect(formatUsage('-5')).toBe('0.0%')
    expect(formatUsage(140)).toBe('100.0%')
  })
})

describe('number formatting', () => {
  it('formats compact numbers for volume', () => {
    expect(formatCompactNumber('41200000')).toBe('41.2M')
  })

  it('formats quantities with up to 4 decimals', () => {
    expect(formatQuantity('40')).toBe('40')
    expect(formatQuantity('1.23456')).toBe('1.2346')
  })
})

describe('pnl semantics', () => {
  it('classifies tone', () => {
    expect(pnlTone('100')).toBe('up')
    expect(pnlTone('-100')).toBe('down')
    expect(pnlTone('0')).toBe('flat')
  })

  it('provides an explicit sign (never color-only)', () => {
    expect(pnlSign('100')).toBe('+')
    expect(pnlSign('-100')).toBe('-')
    expect(pnlSign('0')).toBe('')
  })

  it('formats signed P&L currency', () => {
    expect(formatPnL('1842.35')).toBe('+$1,842.35')
    expect(formatPnL('-183.75')).toBe('-$183.75')
  })
})

describe('duration formatting', () => {
  it('formats seconds to a human string', () => {
    expect(formatDuration(45)).toBe('45s')
    expect(formatDuration(125)).toBe('2m 5s')
    expect(formatDuration(3700)).toBe('1h 1m')
    expect(formatDuration(2419200)).toBe('28d 0h')
    expect(formatDuration(null)).toBe('—')
  })
})
