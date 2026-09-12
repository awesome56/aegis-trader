import type { ISODateString, Numeric } from './api'

export type PositionSide = 'LONG' | 'SHORT'

export interface Position {
  id: string
  symbol: string
  asset_name: string | null
  side: PositionSide
  quantity: Numeric
  average_entry_price: Numeric
  current_price: Numeric | null
  market_value: Numeric
  weight_pct: Numeric
  day_change_pct: Numeric | null
  unrealized_pnl: Numeric
  realized_pnl: Numeric
  return_pct: Numeric
  stop_loss: Numeric | null
  take_profit: Numeric | null
  strategy_id: string | null
  strategy_name: string | null
  opened_at: ISODateString
  updated_at: ISODateString
}

export interface PositionDetail extends Position {
  asset_id: string | null
  proposal_id: string | null
  decision_id: string | null
  orders: PositionOrderRef[]
}

export interface PositionOrderRef {
  id: string
  side: string
  quantity: Numeric
  average_fill_price: Numeric | null
  status: string
  submitted_at: ISODateString | null
}
