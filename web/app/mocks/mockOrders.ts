import type { Order, OrderDetail } from '~/types/order'
import { mockIso } from './helpers'

const ORDERS: Order[] = [
  {
    id: 'ord-nvda-open',
    proposal_id: 'prop-nvda',
    symbol: 'NVDA',
    side: 'BUY',
    order_type: 'MARKET',
    time_in_force: 'DAY',
    status: 'FILLED',
    quantity: '12',
    filled_quantity: '12',
    remaining_quantity: '0',
    limit_price: null,
    stop_price: null,
    average_fill_price: '126.52',
    fees: '0.00',
    idempotency_key: 'idem-nvda-open',
    broker_order_id: 'paper-1001',
    submitted_at: mockIso(0, 1),
    filled_at: mockIso(0, 1),
    cancelled_at: null,
    created_at: mockIso(0, 1),
    updated_at: mockIso(0, 1),
    error_message: null,
  },
  {
    id: 'ord-tsla-pending',
    proposal_id: 'prop-tsla',
    symbol: 'TSLA',
    side: 'BUY',
    order_type: 'LIMIT',
    time_in_force: 'DAY',
    status: 'REJECTED',
    quantity: '18',
    filled_quantity: '0',
    remaining_quantity: '18',
    limit_price: '238.00',
    stop_price: null,
    average_fill_price: null,
    fees: '0.00',
    idempotency_key: 'idem-tsla-pending',
    broker_order_id: null,
    submitted_at: null,
    filled_at: null,
    cancelled_at: null,
    created_at: mockIso(0, 2),
    updated_at: mockIso(0, 2),
    error_message: 'Rejected by risk engine: sector exposure limit.',
  },
]

export function mockOrders(): Order[] {
  return ORDERS.map((order) => ({ ...order }))
}

export function mockOrder(id: string): OrderDetail | null {
  const found = ORDERS.find((order) => order.id === id)
  if (!found) return null
  return {
    ...found,
    executions: found.status === 'FILLED'
      ? [
          {
            id: 'exec-nvda-open',
            order_id: found.id,
            quantity: found.filled_quantity,
            price: found.average_fill_price ?? '0',
            fees: '0.00',
            commission: '0.00',
            slippage: '0.02',
            liquidity: 'taker',
            broker_execution_id: 'be-1001',
            executed_at: mockIso(0, 1),
          },
        ]
      : [],
  }
}
