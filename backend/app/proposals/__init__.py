"""Phase 7 TradeProposal domain package.

`ProposalService` creates and risk-evaluates proposals; `OrderManager` is the
only component allowed to move an approved proposal to a broker order.
"""

from app.proposals.order_manager import OrderManager
from app.proposals.service import ProposalService
from app.proposals.types import ExecutionOutcome, ProposalCreate

__all__ = ["ExecutionOutcome", "OrderManager", "ProposalCreate", "ProposalService"]
