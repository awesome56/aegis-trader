import type { ISODateString, Numeric } from './api'

export type RiskLevel = 'SAFE' | 'WARNING' | 'CRITICAL'

export interface RiskStatus {
  level: RiskLevel
  exposure_pct: Numeric
  max_exposure_pct: Numeric
  daily_pnl: Numeric
  daily_loss_limit: Numeric
  current_drawdown_pct: Numeric
  max_drawdown_pct: Numeric
  open_positions: number
  max_open_positions: number
  trades_today: number
  max_trades_per_day: number
  buying_power: Numeric
  updated_at: ISODateString
}

export interface RiskLimit {
  key: string
  label: string
  current: Numeric
  limit: Numeric
  used_pct: Numeric
  unit: 'percent' | 'currency' | 'count' | 'ratio'
  status: RiskLevel
}

export interface RiskSettings {
  max_position_percentage: Numeric
  max_portfolio_exposure: Numeric
  max_open_positions: number
  max_daily_loss_percentage: Numeric
  max_drawdown_percentage: Numeric
  max_trades_per_day: number
  minimum_confidence: Numeric
  minimum_risk_reward_ratio: Numeric
  max_sector_exposure: Numeric
  max_asset_class_exposure: Numeric
  require_stop_loss: boolean
}

export interface RiskEvent {
  id: string
  level: RiskLevel
  type: string
  message: string
  symbol: string | null
  created_at: ISODateString
}
