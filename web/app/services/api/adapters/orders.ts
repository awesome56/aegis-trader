import type { Paginated } from '~/types/api'
import type { Order, OrderDetail, OrderSide, OrderStatus, OrderType } from '~/types/order'
import { iso, isoOrNull, num } from './common'
import type { RawBrokerOrder, RawBrokerOrderList, RawExecution } from './raw'

export function toOrder(raw: RawBrokerOrder): Order {
  return {
    id: raw.order_id,
    proposal_id: null,
    symbol: raw.symbol,
    side: raw.side as OrderSide,
    order_type: raw.order_type as OrderType,
    time_in_force: raw.time_in_force,
    status: raw.status as OrderStatus,
    quantity: num(raw.quantity),
    filled_quantity: num(raw.filled_quantity),
    remaining_quantity: num(raw.remaining_quantity),
    limit_price: raw.limit_price,
    stop_price: raw.stop_price,
    average_fill_price: raw.average_fill_price,
    fees: num(raw.commission),
    idempotency_key: raw.client_order_id ?? '',
    broker_order_id: raw.broker_order_id,
    submitted_at: isoOrNull(raw.submitted_at),
    filled_at: isoOrNull(raw.filled_at),
    cancelled_at: isoOrNull(raw.cancelled_at),
    created_at: iso(raw.created_at),
    updated_at: iso(raw.updated_at),
    error_message: raw.error_message,
  }
}

export function toOrderList(raw: RawBrokerOrderList): Paginated<Order> {
  return {
    items: raw.items.map(toOrder),
    total: raw.total,
    page: 1,
    pageSize: raw.items.length || 1,
  }
}

export function toExecution(raw: RawExecution) {
  return {
    id: raw.id,
    quantity: num(raw.quantity),
    price: num(raw.price),
    fees: num(raw.fees),
    commission: num(raw.commission),
    slippage: num(raw.slippage),
    liquidity: raw.liquidity,
    broker_execution_id: raw.broker_execution_id,
    executed_at: iso(raw.executed_at),
    gross_amount: raw.gross_amount,
    net_amount: raw.net_amount,
  }
}

export function toOrderDetail(raw: RawBrokerOrder, executions: RawExecution[] = []): OrderDetail {
  return {
    ...toOrder(raw),
    executions: executions.map(toExecution),
  }
}
