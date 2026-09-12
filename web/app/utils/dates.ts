import { format, formatDistanceToNowStrict, isValid, parseISO } from 'date-fns'

function asDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null
  const date = value instanceof Date ? value : parseISO(value)
  return isValid(date) ? date : null
}

export function formatDateTime(value: string | Date | null | undefined): string {
  const date = asDate(value)
  return date ? format(date, 'yyyy-MM-dd HH:mm:ss') : '—'
}

export function formatDate(value: string | Date | null | undefined): string {
  const date = asDate(value)
  return date ? format(date, 'yyyy-MM-dd') : '—'
}

export function formatTime(value: string | Date | null | undefined): string {
  const date = asDate(value)
  return date ? format(date, 'HH:mm:ss') : '—'
}

export function formatShortDate(value: string | Date | null | undefined): string {
  const date = asDate(value)
  return date ? format(date, 'MMM d, HH:mm') : '—'
}

export function formatRelative(value: string | Date | null | undefined): string {
  const date = asDate(value)
  return date ? formatDistanceToNowStrict(date, { addSuffix: true }) : '—'
}

/** Human-readable trade duration from seconds. */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ${Math.round(seconds % 60)}s`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ${minutes % 60}m`
  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h`
}
