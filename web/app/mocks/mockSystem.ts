import type { HealthStatus, SystemStatus } from '~/types/system'
import { mockIso } from './helpers'

export function mockSystemStatus(): SystemStatus {
  return {
    app_name: 'Aegis Trader',
    version: '0.1.0',
    environment: 'development',
    trading_mode: 'paper',
    live_trading_enabled: false,
    live_trading_guard: {
      allowed: false,
      missing_requirements: [
        "TRADING_MODE must be 'live'",
        'LIVE_TRADING_ENABLED must be true',
        'BROKER_LIVE_CREDENTIALS_PRESENT must be true',
        'MANUAL_LIVE_ACTIVATION must be true',
      ],
    },
    broker_provider: 'paper',
    market_data_provider: 'mock',
    agent_enabled: false,
    kill_switch_state: 'TRADING_ENABLED',
    server_time: mockIso(0, 0),
  }
}

export function mockHealth(): HealthStatus {
  return {
    status: 'healthy',
    service: 'Aegis Trader',
    version: '0.1.0',
    environment: 'development',
    timestamp: mockIso(0, 0),
    components: [
      { name: 'database', status: 'healthy', latency_ms: 8.2, detail: null },
      { name: 'redis', status: 'healthy', latency_ms: 1.4, detail: null },
      { name: 'broker', status: 'healthy', latency_ms: 12.0, detail: null },
      { name: 'market_data', status: 'healthy', latency_ms: 22.5, detail: null },
    ],
  }
}
