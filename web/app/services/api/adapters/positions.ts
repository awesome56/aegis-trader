import type { Position, PositionDetail } from '~/types/position'
import { iso } from './common'
import type { RawPositionValuation } from './raw'

export function toPosition(raw: RawPositionValuation): Position {
  return {
    id: raw.id,
    symbol: raw.symbol,
    asset_name: raw.asset_name,
    side: 'LONG',
    quantity: raw.quantity,
    average_entry_price: raw.average_entry_price,
    current_price: raw.current_price,
    market_value: raw.market_value,
    weight_pct: raw.weight_percent,
    day_change_pct: null,
    unrealized_pnl: raw.unrealized_pnl,
    realized_pnl: raw.realized_pnl,
    return_pct: raw.unrealized_return_percent,
    stop_loss: null,
    take_profit: null,
    strategy_id: null,
    strategy_name: null,
    opened_at: iso(raw.opened_at),
    updated_at: iso(raw.updated_at),
  }
}

export function toPositionDetail(raw: RawPositionValuation): PositionDetail {
  return {
    ...toPosition(raw),
    asset_id: null,
    proposal_id: null,
    decision_id: null,
    orders: [],
  }
}
