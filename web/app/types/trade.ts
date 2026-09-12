import type { ISODateString, Numeric } from './api'

export type TradeSide = 'BUY' | 'SELL'
export type TradeStatus = 'OPEN' | 'CLOSED' | 'CANCELLED'

export interface Trade {
  id: string
  symbol: string
  side: TradeSide
  quantity: Numeric
  entry_price: Numeric
  exit_price: Numeric | null
  pnl: Numeric
  return_pct: Numeric
  fees: Numeric
  slippage: Numeric
  strategy_id: string | null
  strategy_name: string | null
  agent_confidence: Numeric | null
  status: TradeStatus
  opened_at: ISODateString
  closed_at: ISODateString | null
  duration_seconds: number | null
}

export interface TradeDetail extends Trade {
  proposal_id: string | null
  decision_id: string | null
  order_ids: string[]
}
