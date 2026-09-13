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


def _fresh_import(package: str, clear_prefixes: tuple[str, ...]) -> set[str]:
    for name in list(sys.modules):
        if name.startswith(clear_prefixes):
            del sys.modules[name]
    importlib.import_module(package)
    return set(sys.modules)


def test_agent_layer_cannot_import_broker_or_orders() -> None:
    modules = _imported_modules_after("app.agents")
    forbidden = [m for m in modules if m.startswith(("app.brokers", "app.orders"))]
    assert forbidden == [], f"Agent layer must not import execution modules: {forbidden}"


def test_strategy_layer_cannot_import_broker_or_orders() -> None:
    modules = _fresh_import(
        "app.strategies",
        ("app.strategies", "app.brokers", "app.orders", "app.risk", "app.agents"),
    )
    forbidden = [
        m for m in modules if m.startswith(("app.brokers", "app.orders", "app.risk", "app.agents"))
    ]
    assert forbidden == [], (
        f"Strategy layer must not import execution/risk/agent modules: {forbidden}"
    )


def test_risk_layer_cannot_import_brokers_or_agents() -> None:
    modules = _fresh_import("app.risk.service", ("app.risk", "app.agents", "app.orders"))
    forbidden = [m for m in modules if m.startswith(("app.agents", "app.orders"))]
    assert forbidden == [], f"Risk layer must not import agent/order modules: {forbidden}"


def test_risk_layer_cannot_import_broker() -> None:
    modules = _imported_modules_after("app.risk")
    forbidden = [m for m in modules if m.startswith("app.brokers")]
    assert forbidden == [], f"Risk layer must not import broker modules: {forbidden}"


def test_market_layer_cannot_import_brokers() -> None:
    modules = _fresh_import("app.market", ("app.market", "app.brokers"))
    forbidden = [m for m in modules if m.startswith("app.brokers")]
    assert forbidden == [], f"Market layer must not import brokers: {forbidden}"


def test_brokers_cannot_import_higher_layers() -> None:
    higher = ("app.risk", "app.agents", "app.strategies", "app.portfolio", "app.orders")
    modules = _fresh_import("app.brokers.paper", ("app.brokers", *higher))
    forbidden = [m for m in modules if m.startswith(higher)]
    assert forbidden == [], f"Broker layer must not import higher layers: {forbidden}"


def test_portfolio_may_depend_on_brokers() -> None:
    # Portfolio sits above the broker: this dependency is expected and allowed.
    modules = _fresh_import("app.portfolio.service", ("app.portfolio", "app.brokers"))
    assert any(m.startswith("app.brokers") for m in modules)


def test_agent_layer_has_no_execution_modules() -> None:
    for name in list(sys.modules):
        if name.startswith(
            ("app.agents", "app.orders", "app.brokers", "app.proposals", "app.risk")
        ):
            del sys.modules[name]
    importlib.import_module("app.agents")
    forbidden_prefixes = (
        "app.orders",
        "app.brokers.paper",
        "app.brokers.base",
        "app.brokers.factory",
        "app.proposals.order_manager",
        "app.risk.trading_state",
        "app.risk.settings_service",
        "app.risk.service",
    )
    forbidden = [m for m in set(sys.modules) if m.startswith(forbidden_prefixes)]
    assert forbidden == [], (
        f"Agent layer must not load execution/risk-mutation modules: {forbidden}"
    )


def test_agent_tool_registry_excludes_execution_tools() -> None:
    from app.agents.tools import FORBIDDEN_TOOLS, READ_TOOLS, WRITE_TOOLS

    available = set(READ_TOOLS) | set(WRITE_TOOLS)
    assert WRITE_TOOLS == ("create_trade_proposal",)
    for name in FORBIDDEN_TOOLS:
        assert name not in available


def test_dependency_direction_agents_to_market_only() -> None:
    # The agent may depend on market/strategy/ai; it must never depend on orders.
    for name in list(sys.modules):
        if name.startswith(("app.agents", "app.orders")):
            del sys.modules[name]
    importlib.import_module("app.agents")
    assert not any(m.startswith("app.orders") for m in sys.modules)
