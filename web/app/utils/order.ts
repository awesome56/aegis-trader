import type { OrderStatus } from '~/types/order'

/** Mirrors the backend broker state machine: terminal orders cannot be cancelled. */
const TERMINAL: ReadonlySet<OrderStatus> = new Set([
  'FILLED',
  'CANCELLED',
  'REJECTED',
  'FAILED',
])

export function isOrderCancellable(status: OrderStatus): boolean {
  return !TERMINAL.has(status)
}

export const ORDER_STATUSES: OrderStatus[] = [
  'CREATED',
  'VALIDATED',
  'SUBMITTED',
  'ACCEPTED',
  'PARTIALLY_FILLED',
  'FILLED',
  'CANCELLED',
  'REJECTED',
  'FAILED',
]
