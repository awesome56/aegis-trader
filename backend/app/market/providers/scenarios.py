"""Deterministic mock-market scenarios.

These scenarios exist to make the **live** deterministic strategy engine
produce realistic, reproducible signals for development and validation. They do
not change strategy thresholds — they simply supply price series that
legitimately satisfy the documented rules.

A scenario defines a close-price series as a pure function of ``count`` (the
window length) and a base price, so a given (scenario, symbol, window) always
yields identical candles. Envelopes control the synthetic high/low range used
for ATR.

This module is intentionally free of provider/DB dependencies so it can be
reused by tests and the seed command.
"""

from __future__ import annotations

import math

SCENARIOS: tuple[str, ...] = (
    "uptrend",
    "downtrend",
    "momentum_bullish",
    "momentum_bearish",
    "mean_reversion_oversold",
    "mean_reversion_overbought",
    "sideways",
    "high_volatility",
)

_ENVELOPE: dict[str, float] = {
    "uptrend": 0.006,
    "downtrend": 0.006,
    "momentum_bullish": 0.004,
    "momentum_bearish": 0.004,
    "mean_reversion_oversold": 0.002,
    "mean_reversion_overbought": 0.002,
    "sideways": 0.002,
    "high_volatility": 0.010,
}


def is_scenario(value: str | None) -> bool:
    return bool(value) and str(value).strip().lower() in SCENARIOS


def normalise_scenario(value: str | None) -> str | None:
    if not is_scenario(value):
        return None
    return str(value).strip().lower()


def envelope(scenario: str) -> float:
    return _ENVELOPE.get(scenario, 0.004)


def scenario_closes(scenario: str, count: int, base: float) -> list[float]:
    """Deterministic close series of length ``count`` starting near ``base``."""
    if count <= 0:
        return []
    if scenario == "uptrend":
        return [base * (1 + 0.004 * index) for index in range(count)]
    if scenario == "downtrend":
        return [base * (1 - 0.004 * index) for index in range(count)]
    if scenario == "momentum_bullish":
        return [
            base * (1 + 0.0004 * index) * (1 + 0.006 * math.sin(index * 0.30 + 2.5))
            for index in range(count)
        ]
    if scenario == "momentum_bearish":
        return [
            base * (1 - 0.0004 * index) * (1 + 0.006 * math.sin(index * 0.45 + 1.5))
            for index in range(count)
        ]
    if scenario == "mean_reversion_oversold":
        closes = [base for _ in range(count)]
        closes[-1] = base * 0.985
        return closes
    if scenario == "mean_reversion_overbought":
        closes = [base for _ in range(count)]
        closes[-1] = base * 1.015
        return closes
    if scenario == "high_volatility":
        return [base * (1 + 0.06 * math.sin(index * 0.7)) for index in range(count)]
    # sideways
    return [base * (1 + 0.0008 * math.sin(index * 1.1)) for index in range(count)]


def scenario_volumes(scenario: str, count: int) -> list[int]:
    """Deterministic volume series. Constant volume yields relative volume 1.0."""
    base_volume = 1_000_000
    if scenario in ("momentum_bullish", "momentum_bearish"):
        return [base_volume * (2 if index >= count - 3 else 1) for index in range(count)]
    return [base_volume for _ in range(count)]
