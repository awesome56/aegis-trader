/**
 * Development-only mock data.
 *
 * These fixtures are returned by the service layer ONLY when
 * `NUXT_PUBLIC_USE_MOCK_API=true`. Production can never silently fall back to
 * them: `isMockEnabled()` defaults to false and must be explicitly enabled.
 */

export function mockIso(daysAgo = 0, hoursAgo = 0): string {
  const date = new Date()
  date.setUTCDate(date.getUTCDate() - daysAgo)
  date.setUTCHours(date.getUTCHours() - hoursAgo)
  return date.toISOString()
}

export const MOCK_PORTFOLIO_ID = '00000000-0000-4000-8000-000000000001'
