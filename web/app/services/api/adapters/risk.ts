import type { RiskLevel, RiskStatus } from '~/types/risk'
import { int, iso, num } from './common'
import type { RawPortfolioSummary, RawRiskUtilization } from './raw'

export interface RiskStatusInput {
  portfolio: RawPortfolioSummary
  riskStatus: string
  utilizations: RawRiskUtilization[]
  updatedAt?: string | null
}

function level(value: string): RiskLevel {
  return value === 'CRITICAL' || value === 'WARNING' ? value : 'SAFE'
}

export function toRiskStatus(input: RiskStatusInput): RiskStatus {
  const rows = new Map(input.utilizations.map((row) => [row.key, row]))
  const exposure = rows.get('portfolio_exposure')
  const positions = rows.get('open_positions')
  const trades = rows.get('trades_today')
  const drawdown = rows.get('drawdown')
  const dailyLoss = rows.get('daily_loss')

  const equity = Number(num(input.portfolio.equity))
  const dailyLossLimit = dailyLoss ? -(Number(dailyLoss.limit) * equity) / 100 : 0

  return {
    level: level(input.riskStatus),
    exposure_pct: exposure ? num(exposure.current) : num(input.portfolio.exposure_percent),
    max_exposure_pct: exposure ? num(exposure.limit) : 0,
    daily_pnl: num(input.portfolio.daily_pnl),
    daily_loss_limit: dailyLossLimit.toFixed(2),
    current_drawdown_pct: drawdown ? num(drawdown.current) : 0,
    max_drawdown_pct: drawdown ? num(drawdown.limit) : 0,
    open_positions: positions ? int(positions.current) : input.portfolio.position_count,
    max_open_positions: positions ? int(positions.limit) : 0,
    trades_today: trades ? int(trades.current) : 0,
    max_trades_per_day: trades ? int(trades.limit) : 0,
    buying_power: num(input.portfolio.buying_power),
    updated_at: iso(input.updatedAt ?? input.portfolio.updated_at),
  }
}
