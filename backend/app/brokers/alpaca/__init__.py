"""Alpaca external broker adapter (Phase 10).

Split into three concerns so each is independently testable:

* :mod:`app.brokers.alpaca.client` — async REST transport (no trading logic)
* :mod:`app.brokers.alpaca.mapping` — pure DTO mapping (no I/O)
* :mod:`app.brokers.alpaca.adapter` — the :class:`~app.brokers.base.BrokerAdapter`

Credentials are held in memory only. The Alpaca *paper* endpoint backs
``BrokerEnvironment.DEMO``; the live endpoint is only reachable when the
server-side live-trading interlock is open.
"""

from app.brokers.alpaca.adapter import AlpacaBrokerAdapter
from app.brokers.alpaca.client import AlpacaClient
from app.brokers.alpaca.mapping import map_account, map_clock, map_order, map_position, map_quote

__all__ = [
    "AlpacaBrokerAdapter",
    "AlpacaClient",
    "map_account",
    "map_clock",
    "map_order",
    "map_position",
    "map_quote",
]
