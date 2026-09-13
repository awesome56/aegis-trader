import type { SignalDirection } from '~/types/market'

/** Maps a strategy signal direction to a proposal side where semantically safe. */
export function signalDirectionToSide(direction: SignalDirection): 'BUY' | 'SELL' | null {
  if (direction === 'LONG') return 'BUY'
  if (direction === 'SHORT') return 'SELL'
  return null
}
