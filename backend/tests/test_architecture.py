"""Architectural boundary guards.

The invariant "no LLM below the Risk Engine line" is enforced by keeping the
agent/strategy layer unable to import broker or order-execution modules. These
tests fail loudly if that boundary is ever crossed.
"""

from __future__ import annotations

import importlib
import sys


def _imported_modules_after(package: str) -> set[str]:
    for name in list(sys.modules):
        if name.startswith(("app.agents", "app.brokers", "app.orders", "app.risk")):
            del sys.modules[name]
    importlib.import_module(package)
    return set(sys.modules)


def test_agent_layer_cannot_import_broker_or_orders() -> None:
    modules = _imported_modules_after("app.agents")
    forbidden = [m for m in modules if m.startswith(("app.brokers", "app.orders"))]
    assert forbidden == [], f"Agent layer must not import execution modules: {forbidden}"


def test_strategy_layer_cannot_import_broker_or_orders() -> None:
    modules = _imported_modules_after("app.strategies")
    forbidden = [m for m in modules if m.startswith(("app.brokers", "app.orders"))]
    assert forbidden == [], f"Strategy layer must not import execution modules: {forbidden}"


def test_risk_layer_cannot_import_broker() -> None:
    modules = _imported_modules_after("app.risk")
    forbidden = [m for m in modules if m.startswith("app.brokers")]
    assert forbidden == [], f"Risk layer must not import broker modules: {forbidden}"
