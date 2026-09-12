import type { RiskEvent, RiskLimit, RiskSettings, RiskStatus } from '~/types/risk'
import { mockIso } from './helpers'

export function mockRiskStatus(): RiskStatus {
  return {
    level: 'WARNING',
    exposure_pct: '67.64',
    max_exposure_pct: '80.00',
    daily_pnl: '1842.35',
    daily_loss_limit: '-2000.00',
    current_drawdown_pct: '3.20',
    max_drawdown_pct: '15.00',
    open_positions: 4,
    max_open_positions: 10,
    trades_today: 3,
    max_trades_per_day: 20,
    buying_power: '82501.50',
    updated_at: mockIso(0, 0),
  }
}

export function mockRiskLimits(): RiskLimit[] {
  return [
    { key: 'max_position_percentage', label: 'Max Position Size', current: '5.00', limit: '5.00', used_pct: '100.00', unit: 'percent', status: 'WARNING' },
    { key: 'max_portfolio_exposure', label: 'Max Portfolio Exposure', current: '67.64', limit: '80.00', used_pct: '84.55', unit: 'percent', status: 'WARNING' },
    { key: 'max_open_positions', label: 'Max Open Positions', current: '4', limit: '10', used_pct: '40.00', unit: 'count', status: 'SAFE' },
    { key: 'max_daily_loss_percentage', label: 'Max Daily Loss', current: '0.00', limit: '2.00', used_pct: '0.00', unit: 'percent', status: 'SAFE' },
    { key: 'max_drawdown_percentage', label: 'Max Drawdown', current: '3.20', limit: '15.00', used_pct: '21.33', unit: 'percent', status: 'SAFE' },
    { key: 'max_trades_per_day', label: 'Max Trades Per Day', current: '3', limit: '20', used_pct: '15.00', unit: 'count', status: 'SAFE' },
    { key: 'minimum_confidence', label: 'Min Agent Confidence', current: '82.00', limit: '60.00', used_pct: '73.17', unit: 'percent', status: 'SAFE' },
    { key: 'minimum_risk_reward_ratio', label: 'Min Risk/Reward', current: '2.18', limit: '2.00', used_pct: '91.74', unit: 'ratio', status: 'WARNING' },
    { key: 'max_sector_exposure', label: 'Max Sector Exposure', current: '46.90', limit: '30.00', used_pct: '100.00', unit: 'percent', status: 'CRITICAL' },
    { key: 'max_asset_class_exposure', label: 'Max Asset-Class Exposure', current: '56.30', limit: '60.00', used_pct: '93.83', unit: 'percent', status: 'WARNING' },
  ]
}

export function mockRiskSettings(): RiskSettings {
  return {
    max_position_percentage: '5.0',
    max_portfolio_exposure: '80.0',
    max_open_positions: 10,
    max_daily_loss_percentage: '2.0',
    max_drawdown_percentage: '15.0',
    max_trades_per_day: 20,
    minimum_confidence: '0.6',
    minimum_risk_reward_ratio: '2.0',
    max_sector_exposure: '30.0',
    max_asset_class_exposure: '60.0',
    require_stop_loss: true,
  }
}

export function mockRiskEvents(): RiskEvent[] {
  return [
    {
      id: 're-1',
      level: 'CRITICAL',
      type: 'sector_exposure',
      message: 'Technology sector exposure exceeds the configured maximum.',
      symbol: null,
      created_at: mockIso(0, 1),
    },
    {
      id: 're-2',
      level: 'WARNING',
      type: 'position_size',
      message: 'NVDA position is at the per-trade size cap.',
      symbol: 'NVDA',
      created_at: mockIso(0, 2),
    },
  ]
}
