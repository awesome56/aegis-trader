import { describe, expect, it } from 'vitest'
import { isOrderCancellable, ORDER_STATUSES } from '~/utils/order'

describe('order cancellation eligibility', () => {
  it('allows cancelling working orders', () => {
    expect(isOrderCancellable('CREATED')).toBe(true)
    expect(isOrderCancellable('SUBMITTED')).toBe(true)
    expect(isOrderCancellable('ACCEPTED')).toBe(true)
    expect(isOrderCancellable('PARTIALLY_FILLED')).toBe(true)
  })

  it('refuses terminal orders', () => {
    expect(isOrderCancellable('FILLED')).toBe(false)
    expect(isOrderCancellable('CANCELLED')).toBe(false)
    expect(isOrderCancellable('REJECTED')).toBe(false)
    expect(isOrderCancellable('FAILED')).toBe(false)
  })

  it('exposes the backend status set', () => {
    expect(ORDER_STATUSES).toContain('PARTIALLY_FILLED')
    expect(ORDER_STATUSES).toHaveLength(9)
  })
})
