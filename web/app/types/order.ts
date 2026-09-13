import type { ISODateString, Numeric } from './api'

export type OrderSide = 'BUY' | 'SELL'
export type OrderType = 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT'
export type OrderStatus =
  | 'CREATED'
  | 'VALIDATED'
  | 'SUBMITTED'
  | 'ACCEPTED'
  | 'PARTIALLY_FILLED'
  | 'FILLED'
  | 'CANCELLED'
  | 'REJECTED'
  | 'FAILED'

export interface Execution {
  id: string
  quantity: Numeric
  price: Numeric
  fees: Numeric
  commission: Numeric
  slippage: Numeric
  liquidity: string | null
  broker_execution_id: string | null
  executed_at: ISODateString
}

export interface Order {
  id: string
  proposal_id: string | null
  symbol: string
  side: OrderSide
  order_type: OrderType
  time_in_force: string
  status: OrderStatus
  quantity: Numeric
  filled_quantity: Numeric
  remaining_quantity: Numeric
  limit_price: Numeric | null
  stop_price: Numeric | null
  average_fill_price: Numeric | null
  fees: Numeric
  idempotency_key: string
  broker_order_id: string | null
  submitted_at: ISODateString | null
  filled_at: ISODateString | null
  cancelled_at: ISODateString | null
  created_at: ISODateString
  updated_at: ISODateString
  error_message: string | null
}

export interface OrderDetail extends Order {
  executions: Execution[]
}
