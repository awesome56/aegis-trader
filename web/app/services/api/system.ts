import type { MessageResponse } from '~/types/api'
import type { HealthStatus, SystemStatus } from '~/types/system'
import { isMockEnabled } from './config'
import { api } from './client'
import { mockHealth, mockSystemStatus } from '~/mocks'

/**
 * System status — IMPLEMENTED (`GET /system/status`, `GET /health`).
 *
 * BACKEND REQUIREMENT (not yet implemented): `POST /system/pause`,
 * `POST /system/resume`, `POST /system/emergency-stop`. The control UI arrives
 * in Phase 6; these methods encode the agreed contract and will 404 until the
 * backend adds them.
 */
export const systemService = {
  getStatus: async (): Promise<SystemStatus> => {
    if (isMockEnabled()) return mockSystemStatus()
    return api.get<SystemStatus>('/system/status')
  },
  getHealth: async (): Promise<HealthStatus> => {
    if (isMockEnabled()) return mockHealth()
    return api.get<HealthStatus>('/health')
  },
  pause: (reason?: string) =>
    api.post<MessageResponse>('/system/pause', reason ? { reason } : undefined),
  resume: () => api.post<MessageResponse>('/system/resume'),
  emergencyStop: (reason: string) =>
    api.post<MessageResponse>('/system/emergency-stop', { reason }),
}
