import { describe, expect, it } from 'vitest'
import {
  toAgentDecisionPage,
  toAgentRunPage,
  toAgentRuntimeStatus,
  toAiProvider,
  toAllocationBreakdown,
  toBacktest,
  toBacktestPage,
  toBacktestResult,
  toCandleSeries,
  toDashboardData,
  toMarketOverview,
  toPortfolioSummary,
  toPosition,
  toProposal,
  toProposalDetail,
  toProposalPage,
  toOrder,
  toExecutionOutcome,
  toQuote,
  toRiskLimits,
  toRiskStatus,
  toActivityPage,
  toNotification,
  toNotificationPage,
  toStrategySignal,
  toStrategySignalPage,
  toStrategy,
  toStrategyDetail,
  toStrategyEvaluation,
  toTrade,
  toTradePage,
  toTradeDetail,
} from '~/services/api/adapters'
import type {
  RawDashboard,
  RawPortfolioHistory,
  RawPositionValuation,
  RawProposal,
  RawProposalPage,
  RawTrade,
  RawTradePage,
  RawSignal,
} from '~/services/api/adapters/raw'

const portfolio = {
  portfolio_id: 'p-1',
  currency: 'USD',
  equity: '127480.25',
  cash: '41250.75',
  buying_power: '82501.50',
  invested_amount: '86229.50',
  market_value: '86229.50',
  realized_pnl: '5320.10',
  unrealized_pnl: '1842.35',
  total_pnl: '27480.25',
  daily_pnl: '1842.35',
  daily_return_percent: '1.47',
  total_return_percent: '27.48',
  exposure_percent: '67.64',
  position_count: 4,
  initial_capital: '100000',
  updated_at: '2026-01-15T15:00:00+00:00',
}

const position: RawPositionValuation = {
  id: 'pos-1',
  symbol: 'AAPL',
  asset_name: 'Apple Inc.',
  asset_class: 'EQUITY',
  sector: 'Tech',
  quantity: '10',
  average_entry_price: '180.00',
  current_price: '190.00',
  market_value: '1900.00',
  cost_basis: '1800.00',
  weight_percent: '12.5',
  unrealized_pnl: '100.00',
  unrealized_return_percent: '5.55',
  realized_pnl: '0',
  opened_at: '2026-01-10T15:00:00+00:00',
  updated_at: '2026-01-15T15:00:00+00:00',
  price_timestamp: '2026-01-15T15:00:00+00:00',
  price_stale: false,
}

const signal: RawSignal = {
  id: 'sig-1',
  strategy_id: 'strat-1',
  strategy_key: 'trend_following',
  strategy_name: 'Trend Following',
  symbol: 'AAPL',
  direction: 'LONG',
  strength: '0.8',
  confidence: '0.9',
  price: '190',
  timeframe: '1D',
  time_horizon: 'SWING',
  market_regime: 'BULLISH',
  indicators: { rsi: '55' },
  signal_time: '2026-01-15T15:00:00+00:00',
  data_timestamp: null,
  expires_at: null,
}

const trade: RawTrade = {
  id: 't-1',
  symbol: 'AAPL',
  side: 'BUY',
  quantity: '10',
  entry_price: '180',
  exit_price: '190',
  pnl: '100',
  fees: '1',
  return_pct: '5.5',
  strategy_id: 'strat-1',
  proposal_id: null,
  order_id: 'o-1',
  opened_at: '2026-01-15T14:00:00+00:00',
  closed_at: '2026-01-15T15:00:00+00:00',
}

const proposal: RawProposal = {
  id: 'pr-1',
  portfolio_id: 'p-1',
  strategy_id: 'strat-1',
  strategy_signal_id: 'sig-1',
  symbol: 'AAPL',
  asset_class: 'EQUITY',
  action: 'BUY',
  order_type: 'MARKET',
  source: 'MANUAL',
  status: 'RISK_APPROVED',
  proposed_quantity: '10',
  proposed_position_percentage: '1.5',
  requested_notional: null,
  entry_price: '190',
  limit_price: null,
  stop_price: null,
  stop_loss: '180',
  take_profit: '220',
  confidence: '0.9',
  time_horizon: 'SWING',
  reasoning_summary: 'breakout',
  market_regime: 'BULLISH',
  failure_reason: null,
  expires_at: '2026-01-15T15:05:00+00:00',
  decided_at: null,
  executed_at: null,
  created_at: '2026-01-15T15:00:00+00:00',
  updated_at: '2026-01-15T15:00:00+00:00',
}

describe('adapters', () => {
  it('maps a raw portfolio summary to the frontend shape', () => {
    const summary = toPortfolioSummary(portfolio as never)
    expect(summary.invested).toBe('86229.50')
    expect(summary.open_pnl).toBe('1842.35')
    expect(summary.daily_return_pct).toBe('1.47')
    expect(summary.total_return_pct).toBe('27.48')
    expect(summary.open_positions).toBe(4)
  })

  it('maps a position valuation', () => {
    const mapped = toPosition(position)
    expect(mapped.side).toBe('LONG')
    expect(mapped.weight_pct).toBe('12.5')
    expect(mapped.return_pct).toBe('5.55')
  })

  it('derives risk status from utilization rows', () => {
    const status = toRiskStatus({
      portfolio: portfolio as never,
      riskStatus: 'WARNING',
      utilizations: [
        { key: 'portfolio_exposure', current: '67.64', limit: '80', utilization_percent: '84.55', status: 'WARNING', unit: 'percent' },
        { key: 'open_positions', current: '4', limit: '10', utilization_percent: '40', status: 'SAFE', unit: 'count' },
        { key: 'trades_today', current: '3', limit: '20', utilization_percent: '15', status: 'SAFE', unit: 'count' },
        { key: 'drawdown', current: '3.2', limit: '15', utilization_percent: '21.33', status: 'SAFE', unit: 'percent' },
      ],
    })
    expect(status.level).toBe('WARNING')
    expect(status.max_exposure_pct).toBe('80')
    expect(status.open_positions).toBe(4)
    expect(status.max_open_positions).toBe(10)
    expect(status.trades_today).toBe(3)
  })

  it('normalises unknown signal directions', () => {
    const mapped = toStrategySignal({ ...signal, direction: 'SIDEWAYS' } as never)
    expect(mapped.direction).toBe('NEUTRAL')
    expect(toStrategySignal(signal).direction).toBe('LONG')
  })

  it('derives trade status and duration', () => {
    const mapped = toTrade(trade)
    expect(mapped.status).toBe('CLOSED')
    expect(mapped.duration_seconds).toBe(3600)
    expect(toTrade({ ...trade, closed_at: null }).status).toBe('OPEN')
  })

  it('maps proposal statuses and pagination', () => {
    expect(toProposal(proposal).status).toBe('RISK_APPROVED')
    expect(toProposal({ ...proposal, status: 'RISK_REJECTED' }).status).toBe('RISK_REJECTED')
    expect(toProposal({ ...proposal, status: 'DRAFT' }).status).toBe('DRAFT')
    expect(toProposal(proposal).source).toBe('MANUAL')
    expect(toProposal(proposal).proposed_position_percentage).toBe('1.5')

    const page = toProposalPage({
      items: [proposal],
      total: 21,
      limit: 5,
      offset: 10,
    } as RawProposalPage)
    expect(page.page).toBe(3)
    expect(page.pageSize).toBe(5)
    expect(page.total).toBe(21)
  })

  it('maps proposal detail with evaluations, orders and executions', () => {
    const detail = toProposalDetail({
      proposal,
      evaluations: [
        {
          id: 'ev-1',
          decision: 'APPROVED',
          symbol: 'AAPL',
          side: 'BUY',
          source: 'manual',
          requested_quantity: '10',
          approved_quantity: '10',
          requested_notional: '1900',
          approved_notional: '1900',
          entry_price: '190',
          stop_loss: '180',
          take_profit: '220',
          estimated_risk_amount: '100',
          risk_reward_ratio: '3',
          portfolio_exposure_before_percent: '10',
          portfolio_exposure_after_percent: '11',
          risk_score: '0.2',
          rules: [
            { key: 'max_position', passed: true, severity: 'WARNING', message: 'ok', current: '1', limit: '5', utilization_percent: '20', metadata: null },
          ],
          reasons: [],
          warnings: [],
          evaluated_at: '2026-01-15T15:00:00+00:00',
        },
      ],
      orders: [
        {
          order_id: 'o-1',
          broker_order_id: 'paper-1',
          client_order_id: 'proposal-pr-1',
          symbol: 'AAPL',
          side: 'BUY',
          order_type: 'MARKET',
          time_in_force: 'DAY',
          quantity: '10',
          filled_quantity: '10',
          remaining_quantity: '0',
          limit_price: null,
          stop_price: null,
          average_fill_price: '190.10',
          commission: '1.00',
          status: 'FILLED',
          error_message: null,
          created_at: '2026-01-15T15:00:01+00:00',
          updated_at: '2026-01-15T15:00:01+00:00',
          submitted_at: '2026-01-15T15:00:01+00:00',
          filled_at: '2026-01-15T15:00:01+00:00',
          cancelled_at: null,
        },
      ],
      executions: [
        {
          id: 'x-1',
          order_id: 'o-1',
          quantity: '10',
          price: '190.10',
          gross_amount: '1901',
          net_amount: '1900',
          fees: '1',
          commission: '1',
          slippage: '0.1',
          broker_execution_id: 'be-1',
          liquidity: 'taker',
          executed_at: '2026-01-15T15:00:01+00:00',
        },
      ],
    } as never)

    expect(detail.proposal.id).toBe('pr-1')
    expect(detail.evaluations[0]?.rules[0]?.passed).toBe(true)
    expect(detail.orders[0]?.remaining_quantity).toBe('0')
    expect(detail.orders[0]?.fees).toBe('1.00')
    expect(detail.executions[0]?.broker_execution_id).toBe('be-1')
  })

  it('maps an order and derives the proposal link from client_order_id', () => {
    const mapped = toOrder({
      order_id: 'o-1',
      broker_order_id: 'paper-1',
      client_order_id: 'proposal-pr-9',
      symbol: 'AAPL',
      side: 'BUY',
      order_type: 'MARKET',
      time_in_force: 'DAY',
      quantity: '10',
      filled_quantity: '4',
      remaining_quantity: '6',
      limit_price: null,
      stop_price: null,
      average_fill_price: '190',
      commission: '1.5',
      status: 'PARTIALLY_FILLED',
      error_message: null,
      created_at: '2026-01-15T15:00:00+00:00',
      updated_at: '2026-01-15T15:00:00+00:00',
      submitted_at: '2026-01-15T15:00:00+00:00',
      filled_at: null,
      cancelled_at: null,
    })
    expect(mapped.id).toBe('o-1')
    expect(mapped.proposal_id).toBe('pr-9')
    expect(mapped.remaining_quantity).toBe('6')
    expect(mapped.fees).toBe('1.5')
    expect(toOrder({ order_id: 'o-2', client_order_id: 'manual-1' } as never).proposal_id).toBeNull()
  })

  it('maps an execution outcome', () => {
    const outcome = toExecutionOutcome({
      proposal_id: 'pr-1',
      executed: false,
      status: 'FAILED',
      order_id: null,
      final_evaluation_id: 'ev-2',
      final_decision: 'REJECTED',
      reason: 'final risk revalidation rejected',
    })
    expect(outcome.executed).toBe(false)
    expect(outcome.final_decision).toBe('REJECTED')
  })

  it('maps an allocation breakdown', () => {
    const breakdown = toAllocationBreakdown({
      total_equity: '127480',
      cash_weight_percent: '32.4',
      by_symbol: [{ label: 'AAPL', value: '12157', weight_percent: '9.5' }],
      by_sector: [{ label: 'Tech', value: '38000', weight_percent: '29.8' }],
      by_asset_class: [{ label: 'EQUITY', value: '86000', weight_percent: '67.4' }],
    })
    expect(breakdown.by_asset[0]).toEqual({ label: 'AAPL', value: '12157', weight_pct: '9.5' })
    expect(breakdown.by_sector[0]?.label).toBe('Tech')
    expect(breakdown.by_asset_class[0]?.weight_pct).toBe('67.4')
  })

  it('maps a market overview and quote', () => {
    const overview = toMarketOverview({
      status: { market: 'US', is_open: true, session: 'REGULAR', opens_at: null, closes_at: null, timestamp: '2026-01-15T15:00:00+00:00', provider: 'mock' },
      provider: 'mock',
      is_open: true,
      session: 'REGULAR',
      as_of: '2026-01-15T15:00:00+00:00',
      items: [
        { symbol: 'AAPL', name: 'Apple', provider: 'mock', price: '190', bid: '189.9', ask: '190.1', previous_close: '188', change: '2', change_pct: '1.2', change_window: 'prev_close', day_high: '192', day_low: '187', volume: 1000, signal_direction: 'LONG', strategy: 'trend', confidence: '0.8', market_regime: 'BULLISH', quote_time: '2026-01-15T15:00:00+00:00', last_candle_time: null, signal_time: null, signal_expires_at: null, age_seconds: 5, is_stale: false, market_closed: false, session: 'OPEN' },
        { symbol: 'MSFT', name: 'Microsoft', provider: 'mock', price: '400', bid: null, ask: null, previous_close: null, change: null, change_pct: null, change_window: null, day_high: null, day_low: null, volume: null, signal_direction: null, strategy: null, confidence: null, market_regime: null, quote_time: null, last_candle_time: null, signal_time: null, signal_expires_at: null, age_seconds: null, is_stale: true, market_closed: false, session: 'OPEN' },
      ],
    })
    expect(overview.items[0]?.signal).toBe('LONG')
    expect(overview.items[0]?.market_regime).toBe('BULLISH')
    expect(overview.items[0]?.bid).toBe('189.9')
    expect(overview.items[0]?.day_high).toBe('192')
    expect(overview.provider).toBe('mock')
    expect(overview.is_open).toBe(true)
    expect(overview.regime).toBe('BULLISH')

    const quote = toQuote({
      symbol: 'AAPL', bid: '189.9', ask: '190.1', last: '190', open: '188', high: '192', low: '187', previous_close: '188', volume: 1000, currency: 'USD', provider: 'mock', market_timestamp: '2026-01-15T15:00:00+00:00', received_at: '2026-01-15T15:00:01+00:00', age_seconds: 1, is_stale: false,
    })
    expect(quote.change).toBe('2.00')
    expect(Number(quote.change_pct)).toBeCloseTo(1.06, 1)
  })

  it('maps candle series timeframes', () => {
    const series = toCandleSeries({
      symbol: 'AAPL',
      timeframe: '1h',
      provider: 'mock',
      candles: [{ open_time: '2026-01-15T14:00:00+00:00', close_time: '2026-01-15T15:00:00+00:00', open: '188', high: '192', low: '187', close: '190', volume: 1000, trade_count: null, vwap: null }],
      is_stale: false,
      age_seconds: 1,
    })
    expect(series.timeframe).toBe('1H')
    expect(series.candles[0]?.time).toBe('2026-01-15T15:00:00+00:00')
  })

  it('maps risk limits from utilizations', () => {
    const limits = toRiskLimits([
      { key: 'portfolio_exposure', current: '67.64', limit: '80', utilization_percent: '84.55', status: 'WARNING', unit: 'percent' },
      { key: 'open_positions', current: '4', limit: '10', utilization_percent: '40', status: 'SAFE', unit: 'count' },
    ])
    expect(limits[0]?.label).toBe('Max Portfolio Exposure')
    expect(limits[0]?.unit).toBe('percent')
    expect(limits[1]?.unit).toBe('count')
  })

  it('maps strategies, signal pages and evaluations', () => {
    const rawStrategy = {
      id: 'strat-1',
      key: 'trend-following',
      name: 'Trend Following',
      description: 'desc',
      strategy_type: 'TREND_FOLLOWING',
      is_enabled: true,
      timeframe: '1d',
      priority: 10,
      parameters: { fast_period: 20 },
      asset_classes: ['EQUITY'],
      signal_count: 5,
      last_signal_at: '2026-01-15T15:00:00+00:00',
      created_at: '2026-01-01T00:00:00+00:00',
      updated_at: '2026-01-15T15:00:00+00:00',
    }
    const strategy = toStrategy(rawStrategy)
    expect(strategy.key).toBe('trend-following')
    expect(strategy.strategy_type).toBe('TREND_FOLLOWING')
    expect(strategy.signal_count).toBe(5)

    const detail = toStrategyDetail({ ...rawStrategy, recent_signals: [signal] })
    expect(detail.recent_signals[0]?.id).toBe('sig-1')

    const page = toStrategySignalPage({
      items: [signal],
      total: 12,
      page: 2,
      page_size: 5,
    })
    expect(page.page).toBe(2)
    expect(page.pageSize).toBe(5)
    expect(page.items[0]?.direction).toBe('LONG')

    const evaluation = toStrategyEvaluation({
      strategy_key: 'momentum',
      strategy_name: 'Momentum',
      symbol: 'AAPL',
      timeframe: '1d',
      status: 'SIGNAL',
      reason: 'signal generated',
      signal: {
        strategy_key: 'momentum',
        strategy_name: 'Momentum',
        symbol: 'AAPL',
        direction: 'LONG',
        strength: '0.8',
        confidence: '0.9',
        price: '190',
        timeframe: '1d',
        time_horizon: 'SWING',
        market_regime: 'BULLISH',
        indicators: { rsi: '61.4' },
        generated_at: '2026-01-15T15:00:00+00:00',
        data_timestamp: '2026-01-15T14:00:00+00:00',
        expires_at: '2026-01-16T15:00:00+00:00',
      },
    })
    expect(evaluation.status).toBe('SIGNAL')
    expect(evaluation.signal?.direction).toBe('LONG')

    const noSignal = toStrategyEvaluation({
      strategy_key: 'momentum',
      strategy_name: 'Momentum',
      symbol: 'AAPL',
      timeframe: '1d',
      status: 'NO_SIGNAL',
      reason: 'no signal',
      signal: null,
    })
    expect(noSignal.signal).toBeNull()
  })

  it('maps notifications and derives structured resource links', () => {
    const withProposal = toNotification({
      id: 'n-1',
      category: 'RISK',
      severity: 'WARNING',
      title: 'Proposal rejected',
      message: 'Exposure limit',
      is_read: false,
      read_at: null,
      payload: { proposal_id: 'pr-9' },
      created_at: '2026-01-15T15:00:00+00:00',
    })
    expect(withProposal.link).toBe('/agent/proposals/pr-9')
    expect(withProposal.is_read).toBe(false)

    const noLink = toNotification({
      id: 'n-2',
      category: 'SYSTEM',
      severity: 'INFO',
      title: 'Info',
      message: 'No resource',
      is_read: true,
      read_at: '2026-01-15T15:01:00+00:00',
      payload: { note: 'x' },
      created_at: '2026-01-15T15:00:00+00:00',
    })
    expect(noLink.link).toBeUndefined()

    const page = toNotificationPage({
      items: [withProposal],
      total: 3,
      page: 1,
      page_size: 10,
    })
    expect(page.pageSize).toBe(10)
    expect(page.items[0]?.link).toBe('/agent/proposals/pr-9')
  })

  it('maps trade pages and detail with open/closed semantics', () => {
    const openTrade = { ...trade, id: 't-open', closed_at: null, exit_price: null }
    const page = toTradePage({ items: [trade, openTrade], total: 2, page: 1, page_size: 50 })
    expect(page.items[0]?.status).toBe('CLOSED')
    expect(page.items[1]?.status).toBe('OPEN')
    expect(page.pageSize).toBe(50)

    const detail = toTradeDetail({ ...trade, proposal_id: 'pr-1', order_id: 'o-1' })
    expect(detail.proposal_id).toBe('pr-1')
    expect(detail.order_ids).toEqual(['o-1'])
  })

  it('normalizes activity source->component and payload->data', () => {
    const page = toActivityPage({
      items: [
        {
          id: 'a-1',
          event_type: 'proposal.executed',
          severity: 'INFO',
          source: 'risk',
          message: 'Proposal executed',
          actor: 'owner',
          correlation_id: 'corr-1',
          payload: { proposal_id: 'pr-1', symbol: 'AAPL' },
          occurred_at: '2026-01-15T15:00:00+00:00',
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
    })
    const event = page.items[0]!
    expect(event.component).toBe('risk')
    expect(event.data).toEqual({ proposal_id: 'pr-1', symbol: 'AAPL' })
    expect(event.symbol).toBe('AAPL')
    expect(event.link).toBe('/agent/proposals/pr-1')
    expect(event.actor).toBe('owner')
    expect(page.pageSize).toBe(50)
  })

  it('maps backtests and results', () => {
    const raw = {
      id: 'bt-1',
      strategy_id: 's-1',
      strategy_name: 'Trend Following',
      name: 'Trend — AAPL',
      symbols: ['AAPL'],
      timeframe: '1d',
      start_date: '2025-01-01',
      end_date: '2025-06-01',
      initial_capital: '100000',
      benchmark_symbol: 'SPY',
      status: 'COMPLETED',
      created_at: '2026-01-15T15:00:00+00:00',
      started_at: '2026-01-15T15:00:00+00:00',
      completed_at: '2026-01-15T15:00:05+00:00',
      error: null,
      final_capital: '112000',
      total_return_pct: '12.00',
      max_drawdown_pct: '6.20',
      num_trades: 8,
    }
    const backtest = toBacktest(raw as never)
    expect(backtest.status).toBe('COMPLETED')
    expect(backtest.total_return_pct).toBe('12.00')

    const page = toBacktestPage({ items: [raw], total: 1, page: 1, page_size: 25 } as never)
    expect(page.pageSize).toBe(25)
    expect(page.items[0]?.symbols).toEqual(['AAPL'])

    const result = toBacktestResult({
      backtest_id: 'bt-1',
      engine_version: 'phase8-v1',
      strategy_config: { strategy: { key: 'trend_following' } },
      metrics: {
        initial_capital: '100000', final_capital: '112000', net_profit: '12000',
        total_return_pct: '12', benchmark_return_pct: '7.4', num_trades: 1,
        wins: 1, losses: 0, win_rate: '100', average_win: '12000', average_loss: '0',
        largest_win: '12000', largest_loss: '0', gross_profit: '12000', gross_loss: '0',
        profit_factor: null, expectancy: '12000', max_drawdown: '0', max_drawdown_pct: '0',
        sharpe_ratio: null, sortino_ratio: null, total_fees: '10', total_slippage: '5',
        average_holding_seconds: '86400', exposure_pct: '50',
      },
      equity_curve: [
        { timestamp: '2026-01-15T15:00:00+00:00', cash: '100000', positions_value: '0', equity: '100000', cumulative_return_pct: '0', drawdown_pct: '0' },
      ],
      drawdown_curve: [{ timestamp: '2026-01-15T15:00:00+00:00', drawdown_pct: '0' }],
      monthly_returns: [{ month: '2025-01', return_pct: '3.2' }],
      trades: [
        { symbol: 'AAPL', side: 'LONG', quantity: '100', entry_time: '2026-01-15T15:00:00+00:00', entry_price: '180', exit_time: '2026-01-16T15:00:00+00:00', exit_price: '190', gross_pnl: '1000', fees: '10', slippage: '5', net_pnl: '985', return_pct: '5.47', holding_period_seconds: 86400, exit_reason: 'SIGNAL' },
      ],
    } as never)
    expect(result.metrics.profit_factor).toBeNull()
    expect(result.equity_curve).toHaveLength(1)
    expect(result.trades[0]?.net_pnl).toBe('985')
    expect(result.monthly_returns[0]?.month).toBe('2025-01')
  })

  it('maps AI providers and agent shapes', () => {
    const provider = toAiProvider({
      id: 'p-1', provider: 'openai', model: 'gpt-4o-mini', base_url: null,
      configured: true, api_key_masked: '••••••1234', enabled: true, is_default: true,
      status: 'CONNECTED', last_tested_at: '2026-01-15T15:00:00+00:00', last_error: null,
      created_at: '2026-01-15T15:00:00+00:00', updated_at: '2026-01-15T15:00:00+00:00',
    })
    expect(provider.status).toBe('CONNECTED')
    expect(provider.api_key_masked).toBe('••••••1234')

    const status = toAgentRuntimeStatus({
      enabled: true, default_mode: 'ANALYSIS_ONLY', provider: 'openai', model: 'gpt-4o-mini',
      provider_status: 'CONNECTED', provider_config_id: 'p-1', running: 0, runs_today: 2,
      recent_failures: 0, last_run: null,
    })
    expect(status.provider).toBe('openai')
    expect(status.last_run).toBeNull()

    const runPage = toAgentRunPage({
      items: [{ id: 'r-1', status: 'COMPLETED', provider: 'openai', model: 'm', mode: 'PROPOSE', symbols: ['AAPL'], prompt: null, error: null, latency_ms: 12, tokens_used: 30, usage: null, proposal_id: 'pr-9', started_at: null, completed_at: null, created_at: '2026-01-15T15:00:00+00:00' }],
      total: 1, page: 1, page_size: 25,
    })
    expect(runPage.items[0]?.mode).toBe('PROPOSE')
    expect(runPage.items[0]?.proposal_id).toBe('pr-9')

    const decisionPage = toAgentDecisionPage({
      items: [{ id: 'd-1', agent_run_id: 'r-1', symbol: 'AAPL', action: 'BUY', confidence: '0.7', reasoning_summary: 'ok', evidence: [{ type: 'strategy_signal', source: 'momentum', direction: 'LONG', confidence: '0.7', data: { rsi: '61' } }], concerns: ['earnings'], proposal_recommended: true, market_regime: 'BULLISH', strategy_signal_ids: ['s-1'], proposal_id: 'pr-9', created_at: '2026-01-15T15:00:00+00:00' }],
      total: 1, page: 1, page_size: 25,
    })
    expect(decisionPage.items[0]?.action).toBe('BUY')
    expect(decisionPage.items[0]?.evidence?.[0]?.source).toBe('momentum')
    expect(decisionPage.items[0]?.concerns).toEqual(['earnings'])
  })

  it('assembles dashboard data from multiple sources', () => {
    const tradesPage: RawTradePage = { items: [trade], total: 1, page: 1, page_size: 5 }
    const proposalsPage: RawProposalPage = { items: [proposal], total: 1, limit: 5, offset: 0 }
    const history: RawPortfolioHistory = {
      range: '1M',
      start: null,
      end: null,
      point_count: 2,
      downsampled: false,
      drawdown_percent: '3.2',
      points: [
        { snapshot_time: '2026-01-14T15:00:00+00:00', equity: '100000', cash: '50000', market_value: '50000', realized_pnl: '0', unrealized_pnl: '0', total_return_percent: '0', daily_pnl: '0', exposure_percent: '50', position_count: 1 },
        { snapshot_time: '2026-01-15T15:00:00+00:00', equity: '101000', cash: '50000', market_value: '51000', realized_pnl: '0', unrealized_pnl: '1000', total_return_percent: '1', daily_pnl: '1000', exposure_percent: '50.5', position_count: 1 },
      ],
    }
    const dashboard: RawDashboard = {
      portfolio: portfolio as never,
      trading_mode: 'paper',
      trading_state: 'TRADING_ENABLED',
      broker_provider: 'paper',
      broker_status: 'PAPER',
      market_data_provider: 'mock',
      market_data_status: 'MOCK',
      market_is_open: true,
      market_session: 'REGULAR',
      risk_status: 'WARNING',
      risk_utilizations: [
        { key: 'trades_today', current: '3', limit: '20', utilization_percent: '15', status: 'SAFE', unit: 'count' },
      ],
      recent_signals: [signal],
      realtime_connections: 1,
      unread_notifications: 0,
      drawdown_percent: '3.2',
      recent_orders: [],
      recent_notifications: [],
      availability: {},
    }

    const data = toDashboardData({
      dashboard,
      positions: [position],
      history,
      trades: tradesPage,
      proposals: proposalsPage,
    })

    expect(data.summary.trades_today).toBe(3)
    expect(data.summary.agent.enabled).toBe(false)
    expect(data.top_positions).toHaveLength(1)
    expect(data.recent_trades).toHaveLength(1)
    expect(data.recent_proposals).toHaveLength(1)
    expect(data.strategy_signals).toHaveLength(1)
    expect(data.equity_history).toHaveLength(2)
  })
})
