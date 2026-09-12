/**
 * Shared API primitives.
 *
 * The backend serialises `Decimal` money values as strings to preserve
 * precision, so numeric fields are typed as `Numeric` and normalised by the
 * formatter utilities rather than trusted as JS numbers.
 */

export type Numeric = number | string

export type ISODateString = string

export interface NumericRange {
  min?: Numeric
  max?: Numeric
}

export type SortDirection = 'asc' | 'desc'

export interface SortState {
  field: string
  direction: SortDirection
}

export interface PageParams {
  page?: number
  pageSize?: number
  search?: string
  sort?: string
  [key: string]: string | number | boolean | undefined
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

/** Normalised error shape produced by the API client. */
export interface ApiErrorShape {
  code: string
  message: string
  status: number
  details?: Record<string, unknown>
}

/** Standard success envelope used by a few backend endpoints. */
export interface MessageResponse {
  detail: string
}

export type Nullable<T> = T | null
