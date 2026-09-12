import type { AllocationBreakdown } from '~/types/portfolio'
import type { Position, PositionDetail } from '~/types/position'
import { mockIso } from './helpers'

const POSITIONS: Position[] = [
  {
    id: 'pos-nvda',
    symbol: 'NVDA',
    asset_name: 'NVIDIA Corporation',
    side: 'LONG',
    quantity: '40',
    average_entry_price: '118.42',
    current_price: '126.85',
    market_value: '5074.00',
    weight_pct: '18.2',
    day_change_pct: '2.14',
    unrealized_pnl: '337.20',
    realized_pnl: '0.00',
    return_pct: '7.12',
    stop_loss: '110.00',
    take_profit: '145.00',
    strategy_id: 'strat-momentum',
    strategy_name: 'Momentum',
    opened_at: mockIso(21),
    updated_at: mockIso(0, 0),
  },
  {
    id: 'pos-aapl',
    symbol: 'AAPL',
    asset_name: 'Apple Inc.',
    side: 'LONG',
    quantity: '55',
    average_entry_price: '214.10',
    current_price: '221.05',
    market_value: '12157.75',
    weight_pct: '15.6',
    day_change_pct: '0.42',
    unrealized_pnl: '382.25',
    realized_pnl: '0.00',
    return_pct: '3.25',
    stop_loss: '200.00',
    take_profit: '240.00',
    strategy_id: 'strat-trend',
    strategy_name: 'Trend Following',
    opened_at: mockIso(34),
    updated_at: mockIso(0, 0),
  },
  {
    id: 'pos-msft',
    symbol: 'MSFT',
    asset_name: 'Microsoft Corporation',
    side: 'LONG',
    quantity: '30',
    average_entry_price: '398.20',
    current_price: '410.55',
    market_value: '12316.50',
    weight_pct: '13.1',
    day_change_pct: '-0.31',
    unrealized_pnl: '370.50',
    realized_pnl: '0.00',
    return_pct: '3.10',
    stop_loss: '380.00',
    take_profit: '450.00',
    strategy_id: 'strat-trend',
    strategy_name: 'Trend Following',
    opened_at: mockIso(40),
    updated_at: mockIso(0, 0),
  },
  {
    id: 'pos-tsla',
    symbol: 'TSLA',
    asset_name: 'Tesla, Inc.',
    side: 'LONG',
    quantity: '25',
    average_entry_price: '243.75',
    current_price: '236.40',
    market_value: '5910.00',
    weight_pct: '9.4',
    day_change_pct: '-1.82',
    unrealized_pnl: '-183.75',
    realized_pnl: '0.00',
    return_pct: '-3.02',
    stop_loss: '225.00',
    take_profit: '290.00',
    strategy_id: 'strat-meanrev',
    strategy_name: 'Mean Reversion',
    opened_at: mockIso(8),
    updated_at: mockIso(0, 0),
  },
]

export function mockPositions(): Position[] {
  return POSITIONS.map((position) => ({ ...position }))
}

export function mockPosition(id: string): PositionDetail | null {
  const found = POSITIONS.find((position) => position.id === id)
  if (!found) return null
  return {
    ...found,
    asset_id: null,
    proposal_id: 'prop-nvda',
    decision_id: 'dec-nvda',
    orders: [
      {
        id: 'ord-nvda-open',
        side: 'BUY',
        quantity: found.quantity,
        average_fill_price: found.average_entry_price,
        status: 'FILLED',
        submitted_at: found.opened_at,
      },
    ],
  }
}

export function mockAllocation(): AllocationBreakdown {
  return {
    by_asset: [
      { label: 'NVDA', value: '5074.00', weight_pct: '18.2' },
      { label: 'AAPL', value: '12157.75', weight_pct: '15.6' },
      { label: 'MSFT', value: '12316.50', weight_pct: '13.1' },
      { label: 'TSLA', value: '5910.00', weight_pct: '9.4' },
      { label: 'Cash', value: '41250.75', weight_pct: '43.7' },
    ],
    by_sector: [
      { label: 'Technology', value: '35622.25', weight_pct: '46.9' },
      { label: 'Consumer Discretionary', value: '5910.00', weight_pct: '9.4' },
      { label: 'Cash', value: '41250.75', weight_pct: '43.7' },
    ],
    by_asset_class: [
      { label: 'Equity', value: '45458.25', weight_pct: '56.3' },
      { label: 'Cash', value: '41250.75', weight_pct: '43.7' },
    ],
  }
}
