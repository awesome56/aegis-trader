import type { Paginated } from '~/types/api'
import type { Trade, TradeDetail, TradeSide, TradeStatus } from '~/types/trade'
import { iso, isoOrNull, num, secondsBetween } from './common'
import type { RawTrade, RawTradePage } from './raw'

function status(raw: RawTrade): TradeStatus {
  return raw.closed_at ? 'CLOSED' : 'OPEN'
}

export function toTrade(raw: RawTrade): Trade {
  return {
    id: raw.id,
    symbol: raw.symbol,
    side: raw.side as TradeSide,
    quantity: num(raw.quantity),
    entry_price: num(raw.entry_price),
    exit_price: raw.exit_price,
    pnl: num(raw.pnl),
    return_pct: num(raw.return_pct),
    fees: num(raw.fees),
    slippage: 0,
    strategy_id: raw.strategy_id,
    strategy_name: null,
    agent_confidence: null,
    status: status(raw),
    opened_at: iso(raw.opened_at),
    closed_at: isoOrNull(raw.closed_at),
    duration_seconds: secondsBetween(raw.opened_at, raw.closed_at),
  }
}

export function toTradePage(raw: RawTradePage): Paginated<Trade> {
  return {
    items: raw.items.map(toTrade),
    total: raw.total,
    page: raw.page,
    pageSize: raw.page_size,
  }
}

export function toTradeDetail(raw: RawTrade): TradeDetail {
  return {
    ...toTrade(raw),
    proposal_id: raw.proposal_id,
    decision_id: null,
    order_ids: raw.order_id ? [raw.order_id] : [],
  }
}
