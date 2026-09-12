"""AI agent layer (Phase 9+).

ARCHITECTURAL BOUNDARY: agents may read state and call ``create_trade_proposal``.
They must never receive broker handles, ``submit_order``/``execute_trade``, or
any callable that bypasses the Risk Engine.
"""
