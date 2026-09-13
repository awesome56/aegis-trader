/**
 * Derive an in-app resource link from structured backend payload metadata.
 * Never parses identifiers out of human-readable message text.
 */
export function resourceLinkFromPayload(
  payload: Record<string, unknown> | null | undefined,
): string | undefined {
  if (!payload) return undefined
  const known: [string, string][] = [
    ['proposal_id', '/agent/proposals'],
    ['order_id', '/orders'],
    ['trade_id', '/trades'],
    ['position_id', '/positions'],
    ['strategy_signal_id', '/strategies'],
    ['strategy_id', '/strategies'],
  ]
  for (const [key, base] of known) {
    const value = payload[key]
    if (typeof value === 'string' && value) return `${base}/${value}`
  }
  return undefined
}
