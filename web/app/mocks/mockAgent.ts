import type { AgentDecision, AgentStatus, TradeProposal } from '~/types/agent'
import { mockIso } from './helpers'

export function mockAgentStatus(): AgentStatus {
  return {
    enabled: false,
    running: false,
    last_analysis_at: mockIso(0, 1),
    next_run_at: null,
    symbols_under_analysis: ['NVDA', 'AAPL', 'MSFT', 'TSLA'],
    decisions_today: 6,
    proposals_today: 3,
    approved_today: 2,
    rejected_today: 1,
    error_count_today: 0,
    last_error: null,
  }
}

export function mockDecisions(): AgentDecision[] {
  return [
    {
      id: 'dec-nvda',
      run_id: 'run-1',
      symbol: 'NVDA',
      action: 'BUY',
      confidence: '0.82',
      market_regime: 'BULLISH',
      reasoning_summary:
        'Trend remains bullish, momentum improving, and volume confirms participation. Exposure stays within limits.',
      evidence: [
        { label: 'Trend', value: 'Bullish', sentiment: 'positive' },
        { label: 'Momentum', value: 'Strong', sentiment: 'positive' },
        { label: 'Volume', value: 'Confirmed', sentiment: 'positive' },
        { label: 'Portfolio exposure', value: 'Acceptable', sentiment: 'neutral' },
      ],
      risk_decision: 'APPROVED',
      proposal_id: 'prop-nvda',
      created_at: mockIso(0, 1),
    },
    {
      id: 'dec-tsla',
      run_id: 'run-1',
      symbol: 'TSLA',
      action: 'BUY',
      confidence: '0.66',
      market_regime: 'HIGH_VOLATILITY',
      reasoning_summary:
        'Momentum turned positive but volatility is elevated; risk engine rejected on sector concentration.',
      evidence: [
        { label: 'Momentum', value: 'Improving', sentiment: 'positive' },
        { label: 'Volatility', value: 'Elevated', sentiment: 'negative' },
        { label: 'Sector exposure', value: 'At limit', sentiment: 'negative' },
      ],
      risk_decision: 'REJECTED',
      proposal_id: 'prop-tsla',
      created_at: mockIso(0, 2),
    },
  ]
}

export function mockProposals(): TradeProposal[] {
  return [
    {
      id: 'prop-nvda',
      portfolio_id: 'port-1',
      strategy_id: 'strat-momentum',
      strategy_signal_id: 'sig-nvda',
      symbol: 'NVDA',
      asset_class: 'EQUITY',
      action: 'BUY',
      order_type: 'MARKET',
      source: 'MANUAL',
      status: 'APPROVED',
      proposed_quantity: '12',
      proposed_position_percentage: '1.2',
      requested_notional: null,
      entry_price: '126.50',
      limit_price: null,
      stop_price: null,
      stop_loss: '118.00',
      take_profit: '145.00',
      confidence: '0.82',
      time_horizon: 'SWING',
      reasoning_summary: 'Trend and momentum aligned with volume confirmation.',
      market_regime: 'BULLISH',
      failure_reason: null,
      expires_at: mockIso(-1, -1),
      decided_at: mockIso(0, 1),
      executed_at: null,
      created_at: mockIso(0, 1),
      updated_at: mockIso(0, 1),
    },
    {
      id: 'prop-tsla',
      portfolio_id: 'port-1',
      strategy_id: 'strat-meanrev',
      strategy_signal_id: null,
      symbol: 'TSLA',
      asset_class: 'EQUITY',
      action: 'BUY',
      order_type: 'MARKET',
      source: 'MANUAL',
      status: 'REJECTED',
      proposed_quantity: '18',
      proposed_position_percentage: '1.8',
      requested_notional: null,
      entry_price: '238.00',
      limit_price: null,
      stop_price: null,
      stop_loss: '228.00',
      take_profit: '262.00',
      confidence: '0.66',
      time_horizon: 'SWING',
      reasoning_summary: 'Stretched intraday move; volatility elevated.',
      market_regime: 'HIGH_VOLATILITY',
      failure_reason: 'Technology sector exposure would exceed the configured limit.',
      expires_at: mockIso(-1, -2),
      decided_at: mockIso(0, 2),
      executed_at: null,
      created_at: mockIso(0, 2),
      updated_at: mockIso(0, 2),
    },
  ]
}
