import type {
  Backtest,
  BacktestMetrics,
  BacktestResult,
  BacktestStatus,
  BacktestTrade,
  EquityCurvePoint,
  MonthlyReturn,
} from '~/types/backtest'
import type { Paginated } from '~/types/api'
import { iso, isoOrNull, num, numOrNull } from './common'
import type {
  RawBacktest,
  RawBacktestMetrics,
  RawBacktestPage,
  RawBacktestResult,
  RawBacktestTrade,
  RawEquityPoint,
} from './raw'

export function toBacktest(raw: RawBacktest): Backtest {
  return {
    id: raw.id,
    name: raw.name,
    strategy_id: raw.strategy_id,
    strategy_name: raw.strategy_name,
    symbols: raw.symbols ?? [],
    timeframe: raw.timeframe,
    start_date: raw.start_date,
    end_date: raw.end_date,
    initial_capital: num(raw.initial_capital),
    benchmark_symbol: raw.benchmark_symbol,
    status: raw.status as BacktestStatus,
    created_at: iso(raw.created_at),
    started_at: isoOrNull(raw.started_at),
    completed_at: isoOrNull(raw.completed_at),
    error: raw.error,
    final_capital: numOrNull(raw.final_capital),
    total_return_pct: numOrNull(raw.total_return_pct),
    max_drawdown_pct: numOrNull(raw.max_drawdown_pct),
    num_trades: raw.num_trades,
  }
}

export function toBacktestPage(raw: RawBacktestPage): Paginated<Backtest> {
  return {
    items: raw.items.map(toBacktest),
    total: raw.total,
    page: raw.page,
    pageSize: raw.page_size,
  }
}

function toMetrics(raw: RawBacktestMetrics): BacktestMetrics {
  return {
    initial_capital: num(raw.initial_capital),
    final_capital: num(raw.final_capital),
    net_profit: num(raw.net_profit),
    total_return_pct: num(raw.total_return_pct),
    benchmark_return_pct: numOrNull(raw.benchmark_return_pct),
    num_trades: raw.num_trades,
    wins: raw.wins,
    losses: raw.losses,
    win_rate: num(raw.win_rate),
    average_win: num(raw.average_win),
    average_loss: num(raw.average_loss),
    largest_win: num(raw.largest_win),
    largest_loss: num(raw.largest_loss),
    gross_profit: num(raw.gross_profit),
    gross_loss: num(raw.gross_loss),
    profit_factor: numOrNull(raw.profit_factor),
    expectancy: num(raw.expectancy),
    max_drawdown: num(raw.max_drawdown),
    max_drawdown_pct: num(raw.max_drawdown_pct),
    sharpe_ratio: numOrNull(raw.sharpe_ratio),
    sortino_ratio: numOrNull(raw.sortino_ratio),
    total_fees: num(raw.total_fees),
    total_slippage: num(raw.total_slippage),
    average_holding_seconds: num(raw.average_holding_seconds),
    exposure_pct: num(raw.exposure_pct),
  }
}

function toEquityPoint(raw: RawEquityPoint): EquityCurvePoint {
  return {
    timestamp: iso(raw.timestamp),
    cash: num(raw.cash),
    positions_value: num(raw.positions_value),
    equity: num(raw.equity),
    cumulative_return_pct: num(raw.cumulative_return_pct),
    drawdown_pct: num(raw.drawdown_pct),
  }
}

function toTrade(raw: RawBacktestTrade): BacktestTrade {
  return {
    symbol: raw.symbol,
    side: raw.side,
    quantity: num(raw.quantity),
    entry_time: iso(raw.entry_time),
    entry_price: num(raw.entry_price),
    exit_time: iso(raw.exit_time),
    exit_price: num(raw.exit_price),
    gross_pnl: num(raw.gross_pnl),
    fees: num(raw.fees),
    slippage: num(raw.slippage),
    net_pnl: num(raw.net_pnl),
    return_pct: num(raw.return_pct),
    holding_period_seconds: raw.holding_period_seconds,
    exit_reason: raw.exit_reason,
  }
}

export function toBacktestResult(raw: RawBacktestResult): BacktestResult {
  return {
    backtest_id: raw.backtest_id,
    engine_version: raw.engine_version,
    strategy_config: raw.strategy_config,
    metrics: toMetrics(raw.metrics),
    equity_curve: raw.equity_curve.map(toEquityPoint),
    drawdown_curve: (raw.drawdown_curve ?? []).map((point) => ({
      timestamp: iso(point.timestamp),
      drawdown_pct: num(point.drawdown_pct),
    })),
    monthly_returns: (raw.monthly_returns ?? []).map<MonthlyReturn>((row) => ({
      month: row.month,
      return_pct: num(row.return_pct),
    })),
    trades: (raw.trades ?? []).map(toTrade),
  }
}
