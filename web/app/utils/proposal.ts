import type { OrderType } from '~/types/order'

export interface ProposalFormFields {
  symbol: string
  sizeMode: 'quantity' | 'notional'
  quantity: string
  notional: string
  orderType: OrderType
  limitPrice: string
  stopPrice: string
  stopLoss: string
  takeProfit: string
  confidence: string
}

function positive(value: string): boolean {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0
}

/** Mirrors the backend ProposalCreate validator so failures surface before submit. */
export function proposalFormErrors(fields: ProposalFormFields): string[] {
  const errors: string[] = []
  if (!fields.symbol.trim()) errors.push('Symbol is required.')
  if (fields.sizeMode === 'quantity' && !positive(fields.quantity)) {
    errors.push('Quantity must be greater than 0.')
  }
  if (fields.sizeMode === 'notional' && !positive(fields.notional)) {
    errors.push('Notional must be greater than 0.')
  }
  const requiresLimit = fields.orderType === 'LIMIT' || fields.orderType === 'STOP_LIMIT'
  const requiresStop = fields.orderType === 'STOP' || fields.orderType === 'STOP_LIMIT'
  if (requiresLimit && !positive(fields.limitPrice)) {
    errors.push('A limit price is required for this order type.')
  }
  if (requiresStop && !positive(fields.stopPrice)) {
    errors.push('A stop price is required for this order type.')
  }
  if (fields.stopLoss && !positive(fields.stopLoss)) {
    errors.push('Stop loss must be greater than 0.')
  }
  if (fields.takeProfit && !positive(fields.takeProfit)) {
    errors.push('Take profit must be greater than 0.')
  }
  const confidence = Number(fields.confidence)
  if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
    errors.push('Confidence must be between 0 and 1.')
  }
  return errors
}
