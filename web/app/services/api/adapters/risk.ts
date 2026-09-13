import type { RiskEvent, RiskLevel, RiskLimit, RiskSettings, RiskStatus } from '~/types/risk'
import { int, iso, num } from './common'
import type { RawPortfolioSummary, RawRiskEvent, RawRiskOverview, RawRiskSettings, RawRiskUtilization } from './raw'

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

export function toRiskStatusFromOverview(raw: RawRiskOverview): RiskStatus {
  const equity = Number(num(raw.equity))
  const exposureRow = raw.utilizations.find((row) => row.key === 'portfolio_exposure')
  return {
    level: level(raw.status),
    exposure_pct: num(raw.portfolio_exposure_percent),
    max_exposure_pct: exposureRow ? num(exposureRow.limit) : 0,
    daily_pnl: num(raw.daily_pnl),
    daily_loss_limit: (-(Number(raw.daily_loss_limit_percent) * equity) / 100).toFixed(2),
    current_drawdown_pct: num(raw.current_drawdown_percent),
    max_drawdown_pct: num(raw.max_drawdown_percent),
    open_positions: raw.open_positions,
    max_open_positions: raw.max_open_positions,
    trades_today: raw.trades_today,
    max_trades_per_day: raw.max_trades_per_day,
    buying_power: num(raw.buying_power),
    updated_at: iso(raw.updated_at),
  }
}

const LIMIT_LABELS: Record<string, string> = {
  portfolio_exposure: 'Max Portfolio Exposure',
  max_position: 'Max Position Size',
  open_positions: 'Max Open Positions',
  trades_today: 'Max Trades Per Day',
  drawdown: 'Max Drawdown',
  sector_exposure: 'Max Sector Exposure',
  asset_class_exposure: 'Max Asset-Class Exposure',
  daily_loss: 'Max Daily Loss',
}

export function toRiskLimits(utilizations: RawRiskUtilization[]): RiskLimit[] {
  return utilizations.map((row) => ({
    key: row.key,
    label: LIMIT_LABELS[row.key] ?? row.key,
    current: num(row.current),
    limit: num(row.limit),
    used_pct: num(row.utilization_percent),
    unit: row.unit === 'count' ? 'count' : 'percent',
    status: level(row.status),
  }))
}

export function toRiskSettings(raw: RawRiskSettings): RiskSettings {
  return {
    max_position_percentage: num(raw.max_position_percent),
    max_portfolio_exposure: num(raw.max_portfolio_exposure_percent),
    max_open_positions: raw.max_open_positions,
    max_daily_loss_percentage: num(raw.max_daily_loss_percent),
    max_drawdown_percentage: num(raw.max_drawdown_percent),
    max_trades_per_day: raw.max_trades_per_day,
    minimum_confidence: num(raw.min_strategy_confidence),
    minimum_risk_reward_ratio: num(raw.min_reward_risk_ratio),
    max_sector_exposure: num(raw.max_sector_exposure_percent),
    max_asset_class_exposure: num(raw.max_asset_class_exposure_percent),
    require_stop_loss: raw.require_stop_loss,
  }
}

export function toRiskSettingsPatch(settings: Partial<RiskSettings>): Record<string, unknown> {
  const patch: Record<string, unknown> = {}
  const map: Record<keyof RiskSettings, string> = {
    max_position_percentage: 'max_position_percent',
    max_portfolio_exposure: 'max_portfolio_exposure_percent',
    max_open_positions: 'max_open_positions',
    max_daily_loss_percentage: 'max_daily_loss_percent',
    max_drawdown_percentage: 'max_drawdown_percent',
    max_trades_per_day: 'max_trades_per_day',
    minimum_confidence: 'min_strategy_confidence',
    minimum_risk_reward_ratio: 'min_reward_risk_ratio',
    max_sector_exposure: 'max_sector_exposure_percent',
    max_asset_class_exposure: 'max_asset_class_exposure_percent',
    require_stop_loss: 'require_stop_loss',
  }
  for (const [key, value] of Object.entries(settings)) {
    const target = map[key as keyof RiskSettings]
    if (target && value !== undefined) patch[target] = value
  }
  return patch
}

export function toRiskEvents(raw: RawRiskEvent[]): RiskEvent[] {
  return raw.map((event) => ({
    id: event.id,
    level: event.severity === 'CRITICAL' ? 'CRITICAL' : event.severity === 'WARNING' ? 'WARNING' : 'SAFE',
    type: event.event_type,
    message: event.message,
    symbol: typeof event.payload?.symbol === 'string' ? event.payload.symbol : null,
    created_at: iso(event.occurred_at),
  }))
}
