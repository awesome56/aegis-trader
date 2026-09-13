import { describe, expect, it } from 'vitest'
import { proposalFormErrors } from '~/utils/proposal'

const base = {
  symbol: 'AAPL',
  sizeMode: 'quantity' as const,
  quantity: '10',
  notional: '',
  orderType: 'MARKET' as const,
  limitPrice: '',
  stopPrice: '',
  stopLoss: '180',
  takeProfit: '220',
  confidence: '0.7',
}

describe('proposalFormErrors', () => {
  it('accepts a valid market proposal', () => {
    expect(proposalFormErrors(base)).toEqual([])
  })

  it('requires a symbol', () => {
    expect(proposalFormErrors({ ...base, symbol: '' })).toContain('Symbol is required.')
  })

  it('requires quantity in quantity mode', () => {
    expect(proposalFormErrors({ ...base, quantity: '0' })).toContain('Quantity must be greater than 0.')
  })

  it('requires notional in notional mode', () => {
    const fields = { ...base, sizeMode: 'notional' as const, notional: '' }
    expect(proposalFormErrors(fields)).toContain('Notional must be greater than 0.')
  })

  it('requires a limit price for LIMIT and STOP_LIMIT', () => {
    expect(proposalFormErrors({ ...base, orderType: 'LIMIT' })).toContain(
      'A limit price is required for this order type.',
    )
    expect(
      proposalFormErrors({ ...base, orderType: 'STOP_LIMIT', limitPrice: '190', stopPrice: '185' }),
    ).toEqual([])
  })

  it('requires a stop price for STOP and STOP_LIMIT', () => {
    expect(proposalFormErrors({ ...base, orderType: 'STOP' })).toContain(
      'A stop price is required for this order type.',
    )
  })

  it('validates confidence range', () => {
    expect(proposalFormErrors({ ...base, confidence: '1.4' })).toContain(
      'Confidence must be between 0 and 1.',
    )
  })
})
