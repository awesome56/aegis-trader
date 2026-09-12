import type { AgentDecision, AgentStatus, ProposalPipeline, TradeProposal } from '~/types/agent'
import { mockSignals } from './mockStrategies'
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
      symbol: 'NVDA',
      asset_class: 'EQUITY',
      action: 'BUY',
      order_type: 'MARKET',
      proposed_quantity: '12',
      proposed_position_pct: '1.2',
      entry_price: '126.50',
      stop_loss: '118.00',
      take_profit: '145.00',
      risk_reward_ratio: '2.18',
      confidence: '0.82',
      time_horizon: 'SWING',
      strategy_id: 'strat-momentum',
      strategy_name: 'Momentum',
      reasoning_summary: 'Trend and momentum aligned with volume confirmation.',
      status: 'APPROVED',
      risk_decision: 'APPROVED',
      created_at: mockIso(0, 1),
      expires_at: mockIso(-1, -1),
    },
    {
      id: 'prop-tsla',
      symbol: 'TSLA',
      asset_class: 'EQUITY',
      action: 'BUY',
      order_type: 'MARKET',
      proposed_quantity: '18',
      proposed_position_pct: '1.8',
      entry_price: '238.00',
      stop_loss: '228.00',
      take_profit: '262.00',
      risk_reward_ratio: '2.40',
      confidence: '0.66',
      time_horizon: 'SWING',
      strategy_id: 'strat-meanrev',
      strategy_name: 'Mean Reversion',
      reasoning_summary: 'Stretched intraday move; volatility elevated.',
      status: 'REJECTED',
      risk_decision: 'REJECTED',
      created_at: mockIso(0, 2),
      expires_at: mockIso(-1, -2),
    },
  ]
}

export function mockProposalPipeline(id: string): ProposalPipeline | null {
  const proposal = mockProposals().find((entry) => entry.id === id)
  if (!proposal) return null
  const approved = proposal.risk_decision === 'APPROVED'
  return {
    proposal,
    signals: mockSignals().filter((signal) => signal.symbol === proposal.symbol),
    decision: mockDecisions().find((decision) => decision.proposal_id === id) ?? null,
    risk_evaluation: {
      id: `risk-${id}`,
      decision: approved ? 'APPROVED' : 'REJECTED',
      risk_score: approved ? '0.18' : '0.71',
      approved_quantity: approved ? proposal.proposed_quantity : null,
      risk_reward_ratio: proposal.risk_reward_ratio,
      checks: [
        { name: 'max_position_percentage', passed: true },
        { name: 'max_portfolio_exposure', passed: true },
        {
          name: 'max_sector_exposure',
          passed: approved,
          detail: approved ? undefined : 'Technology exposure would exceed the configured limit.',
        },
        { name: 'minimum_risk_reward_ratio', passed: true },
      ],
      reasons: approved
        ? ['All deterministic risk checks passed.']
        : ['Technology sector exposure would exceed the configured limit.'],
      warnings: approved ? ['Position sized near the per-trade cap.'] : [],
      evaluated_at: mockIso(0, 1),
    },
    order: approved
      ? {
          id: `ord-${id}`,
          proposal_id: id,
          symbol: proposal.symbol,
          side: 'BUY',
          order_type: 'MARKET',
          status: 'FILLED',
          quantity: proposal.proposed_quantity,
          filled_quantity: proposal.proposed_quantity,
          limit_price: null,
          stop_price: null,
          average_fill_price: proposal.entry_price,
          fees: '0.00',
          idempotency_key: `idem-${id}`,
          broker_order_id: `paper-${id}`,
          submitted_at: mockIso(0, 1),
          filled_at: mockIso(0, 1),
          cancelled_at: null,
          created_at: mockIso(0, 1),
          updated_at: mockIso(0, 1),
          error_message: null,
        }
      : null,
    executions: approved
      ? [
          {
            id: `exec-${id}`,
            quantity: proposal.proposed_quantity,
            price: proposal.entry_price ?? '0',
            fees: '0.00',
            commission: '0.00',
            slippage: '0.01',
            liquidity: 'taker',
            broker_execution_id: `be-${id}`,
            executed_at: mockIso(0, 1),
          },
        ]
      : [],
  }
}
