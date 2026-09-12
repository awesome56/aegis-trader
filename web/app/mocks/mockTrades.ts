import type { Trade, TradeDetail } from '~/types/trade'
import { mockIso } from './helpers'

const TRADES: Trade[] = [
  {
    id: 'trade-1',
    symbol: 'MSFT',
    side: 'BUY',
    quantity: '30',
    entry_price: '398.20',
    exit_price: '410.55',
    pnl: '370.50',
    return_pct: '3.10',
    fees: '1.20',
    slippage: '0.45',
    strategy_id: 'strat-trend',
    strategy_name: 'Trend Following',
    agent_confidence: '0.74',
    status: 'CLOSED',
    opened_at: mockIso(40),
    closed_at: mockIso(12),
    duration_seconds: 2419200,
  },
  {
    id: 'trade-2',
    symbol: 'AMZN',
    side: 'BUY',
    quantity: '50',
    entry_price: '181.10',
    exit_price: '188.40',
    pnl: '365.00',
    return_pct: '4.03',
    fees: '1.00',
    slippage: '0.30',
    strategy_id: 'strat-momentum',
    strategy_name: 'Momentum',
    agent_confidence: '0.69',
    status: 'CLOSED',
    opened_at: mockIso(30),
    closed_at: mockIso(9),
    duration_seconds: 1814400,
  },
  {
    id: 'trade-3',
    symbol: 'TSLA',
    side: 'SELL',
    quantity: '20',
    entry_price: '245.00',
    exit_price: '236.40',
    pnl: '172.00',
    return_pct: '3.51',
    fees: '0.80',
    slippage: '0.25',
    strategy_id: 'strat-meanrev',
    strategy_name: 'Mean Reversion',
    agent_confidence: '0.61',
    status: 'CLOSED',
    opened_at: mockIso(6),
    closed_at: mockIso(1),
    duration_seconds: 432000,
  },
]

export function mockTrades(): Trade[] {
  return TRADES.map((trade) => ({ ...trade }))
}

export function mockTrade(id: string): TradeDetail | null {
  const found = TRADES.find((trade) => trade.id === id)
  if (!found) return null
  return {
    ...found,
    proposal_id: 'prop-nvda',
    decision_id: 'dec-nvda',
    order_ids: ['ord-nvda-open'],
  }
}
