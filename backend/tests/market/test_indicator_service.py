"""Indicator service tests (bundles, configuration, empty input)."""

from __future__ import annotations

import pytest
from app.market.enums import Timeframe
from app.market.providers.mock import MockMarketDataProvider
from app.market.services.indicator_service import IndicatorConfig, IndicatorService
from pydantic import ValidationError


async def _candles(provider: MockMarketDataProvider, limit: int = 120):  # noqa: ANN202
    return await provider.get_latest_candles("AAPL", Timeframe.ONE_HOUR, limit)


async def test_bundle_full(mock_provider: MockMarketDataProvider) -> None:
    candles = await _candles(mock_provider, 120)
    bundle = IndicatorService().calculate_indicators(candles)

    assert bundle.symbol == "AAPL"
    assert bundle.timeframe == "1h"
    assert bundle.price == float(candles[-1].close)
    assert bundle.data_timestamp == candles[-1].close_time
    assert bundle.sma.has_sufficient_data
    assert bundle.sma.latest is not None
    assert bundle.ema.latest is not None
    assert bundle.rsi.latest is not None and 0 <= bundle.rsi.latest <= 100
    assert bundle.atr.latest is not None and bundle.atr.latest > 0
    assert bundle.macd.latest_macd is not None
    assert bundle.bollinger.latest_upper is not None
    assert bundle.bollinger.latest_lower is not None
    assert bundle.bollinger.latest_upper >= bundle.bollinger.latest_middle
    assert bundle.bollinger.latest_lower <= bundle.bollinger.latest_middle
    assert bundle.volume.current_volume is not None
    # points() drops warm-up Nones: n - (period - 1)
    assert len(bundle.sma.values) == 120 - 19


async def test_insufficient_history_yields_no_latest(mock_provider: MockMarketDataProvider) -> None:
    candles = await _candles(mock_provider, 5)
    bundle = IndicatorService().calculate_indicators(candles)
    assert bundle.sma.has_sufficient_data is False
    assert bundle.sma.latest is None
    assert bundle.bollinger.latest_middle is None


async def test_custom_configuration(mock_provider: MockMarketDataProvider) -> None:
    candles = await _candles(mock_provider, 60)
    service = IndicatorService(IndicatorConfig(sma_period=5, ema_period=5, rsi_period=7))
    bundle = service.calculate_indicators(candles)
    assert bundle.sma.period == 5
    assert bundle.ema.period == 5
    assert bundle.rsi.period == 7


async def test_individual_calculations(mock_provider: MockMarketDataProvider) -> None:
    candles = await _candles(mock_provider, 60)
    service = IndicatorService()
    assert service.calculate_sma(candles, 10).period == 10
    assert service.calculate_rsi(candles, 14).latest is not None
    macd = service.calculate_macd(candles, 5, 10, 4)
    assert macd.fast_period == 5 and macd.slow_period == 10
    assert service.calculate_atr(candles, 5).latest is not None
    assert service.calculate_bollinger(candles, 10, 1.5).std_dev == 1.5
    assert service.calculate_volume(candles, 10).ma_period == 10


def test_empty_candles_are_safe() -> None:
    bundle = IndicatorService().calculate_indicators([])
    assert bundle.symbol is None
    assert bundle.price is None
    assert bundle.sma.latest is None
    assert bundle.macd.latest_macd is None


def test_invalid_config_rejected() -> None:
    with pytest.raises(ValidationError):
        IndicatorConfig(macd_fast=26, macd_slow=12)
    with pytest.raises(ValidationError):
        IndicatorConfig(sma_period=0)
