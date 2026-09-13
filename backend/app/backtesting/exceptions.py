"""Backtesting exceptions."""

from __future__ import annotations

from app.core.exceptions import AegisError


class BacktestError(AegisError):
    code = "backtest_error"
    status_code = 400


class BacktestValidationError(BacktestError):
    code = "backtest_validation_error"


class BacktestInsufficientData(BacktestError):
    code = "backtest_insufficient_data"


class BacktestDataError(BacktestError):
    code = "backtest_data_error"
