"""Market-data validation and decimal-helper tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.market.domain.models import Candle, MarketQuote
from app.market.enums import Timeframe
from app.market.exceptions import InvalidMarketDataError
from app.market.validation import (
    dedupe_candles,
    normalize_symbol,
    to_decimal,
    validate_candle,
    validate_quote,
)

NOW = datetime(2026, 1, 15, 15, 0, tzinfo=UTC)


def _candle(**overrides: object) -> Candle:
    values: dict[str, object] = {
        "symbol": "AAPL",
        "timeframe": Timeframe.ONE_HOUR,
        "open_time": NOW,
        "open": Decimal("100"),
        "high": Decimal("102"),
        "low": Decimal("99"),
        "close": Decimal("101"),
        "volume": 1000,
        "provider": "test",
    }
    values.update(overrides)
    return Candle(**values)  # type: ignore[arg-type]


def _quote(**overrides: object) -> MarketQuote:
    values: dict[str, object] = {
        "symbol": "AAPL",
        "last": Decimal("100"),
        "bid": Decimal("99.99"),
        "ask": Decimal("100.01"),
        "volume": 1000,
        "provider": "test",
        "market_timestamp": NOW,
        "received_at": NOW,
    }
    values.update(overrides)
    return MarketQuote(**values)  # type: ignore[arg-type]


def test_to_decimal_avoids_float_artefacts() -> None:
    assert to_decimal(126.85) == Decimal("126.8500")
    assert to_decimal("126.85") == Decimal("126.8500")


def test_normalize_symbol() -> None:
    assert normalize_symbol(" aapl ") == "AAPL"
    with pytest.raises(InvalidMarketDataError):
        normalize_symbol("   ")


def test_valid_candle_passes() -> None:
    assert validate_candle(_candle()) is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"high": Decimal("98")},  # high below open/close
        {"low": Decimal("101")},  # low above open/close
        {"open": Decimal("0")},
        {"close": Decimal("-1")},
        {"volume": -5},
    ],
)
def test_invalid_candles_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidMarketDataError):
        validate_candle(_candle(**overrides))


def test_candle_close_time_must_follow_open() -> None:
    with pytest.raises(InvalidMarketDataError):
        validate_candle(_candle(close_time=datetime(2026, 1, 15, 14, 0, tzinfo=UTC)))


def test_invalid_quotes_rejected() -> None:
    with pytest.raises(InvalidMarketDataError):
        validate_quote(_quote(last=Decimal("0")))
    with pytest.raises(InvalidMarketDataError):
        validate_quote(_quote(bid=Decimal("101"), ask=Decimal("100")))
    with pytest.raises(InvalidMarketDataError):
        validate_quote(_quote(volume=-1))


def test_dedupe_keeps_last_and_sorts() -> None:
    earlier = _candle(open_time=NOW.replace(hour=10), close=Decimal("100"))
    later_first = _candle(open_time=NOW.replace(hour=11), close=Decimal("101"))
    later_updated = _candle(open_time=NOW.replace(hour=11), close=Decimal("102"))
    result = dedupe_candles([later_first, earlier, later_updated])
    assert [c.open_time.hour for c in result] == [10, 11]
    assert result[-1].close == Decimal("102")


def test_symbol_and_asset_id_round_trip() -> None:
    asset_id = uuid.uuid4()
    candle = _candle(asset_id=asset_id, symbol="aapl")
    assert candle.symbol == "AAPL"
    assert candle.asset_id == asset_id
