"""Market-data validation and decimal helpers.

Financial values must never be built from binary floats without quantisation:
``Decimal(126.85)`` carries float artefacts. Providers use :func:`to_decimal`
so prices are constructed from their string form and quantised consistently.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.market.domain.models import Candle, MarketQuote
from app.market.exceptions import InvalidMarketDataError

# 4 decimal places covers sub-cent instruments without inventing precision.
PRICE_PLACES = Decimal("0.0001")


def to_decimal(value: Decimal | int | float | str) -> Decimal:
    """Convert a value to a quantised Decimal without float artefacts."""
    if isinstance(value, Decimal):
        return value.quantize(PRICE_PLACES, rounding=ROUND_HALF_UP)
    try:
        return Decimal(str(value)).quantize(PRICE_PLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise InvalidMarketDataError(f"Invalid numeric value: {value!r}") from exc


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise InvalidMarketDataError("Symbol must not be empty")
    return normalized


_FIAT = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNH", "MXN", "ZAR", "NGN"}
_CRYPTO_QUOTES = {"USDT", "USDC", "BUSD", "BTC", "ETH"}


def detect_asset_class(symbol: str):  # noqa: ANN201
    """Classify a symbol as EQUITY / FOREX / CRYPTO / ETF (best-effort)."""
    from app.models.enums import AssetClass

    normalized = normalize_symbol(symbol)
    if "/" in normalized or "-" in normalized:
        base, _, quote = normalized.replace("-", "/").partition("/")
        if quote in _CRYPTO_QUOTES or base in {"BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "XBT"}:
            return AssetClass.CRYPTO
        if base in _FIAT and quote in _FIAT:
            return AssetClass.FOREX
        return AssetClass.CRYPTO
    if normalized in {"SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "GLD", "SLV"}:
        return AssetClass.ETF
    return AssetClass.EQUITY


def external_symbol(symbol: str, provider: str) -> str:
    """Map an internal symbol to a provider's wire format."""
    normalized = normalize_symbol(symbol)
    provider = provider.lower()
    if provider == "kraken":
        base, _, quote = normalized.replace("-", "/").partition("/")
        if not quote:
            return normalized
        base = "XBT" if base == "BTC" else base
        return f"{base}{quote}"
    if provider == "twelvedata":
        return normalized.replace("-", "/")
    return normalized


def validate_quote(quote: MarketQuote) -> MarketQuote:
    """Reject impossible quotes. Returns the quote for convenient chaining."""
    if quote.last <= 0:
        raise InvalidMarketDataError(f"Quote last price must be positive for {quote.symbol}")
    for name, price in (("bid", quote.bid), ("ask", quote.ask)):
        if price is not None and price <= 0:
            raise InvalidMarketDataError(f"Quote {name} must be positive for {quote.symbol}")
    if quote.bid is not None and quote.ask is not None and quote.bid > quote.ask:
        raise InvalidMarketDataError(
            f"Quote bid ({quote.bid}) cannot exceed ask ({quote.ask}) for {quote.symbol}"
        )
    if quote.volume is not None and quote.volume < 0:
        raise InvalidMarketDataError(f"Quote volume must not be negative for {quote.symbol}")
    return quote


def validate_candle(candle: Candle) -> Candle:
    """Reject impossible candles. Returns the candle for convenient chaining."""
    for name in ("open", "high", "low", "close"):
        if getattr(candle, name) <= 0:
            raise InvalidMarketDataError(
                f"Candle {name} must be positive for {candle.symbol} @ {candle.open_time}"
            )
    if candle.high < candle.low:
        raise InvalidMarketDataError(f"Candle high < low for {candle.symbol} @ {candle.open_time}")
    if candle.high < candle.open or candle.high < candle.close:
        raise InvalidMarketDataError(
            f"Candle high below open/close for {candle.symbol} @ {candle.open_time}"
        )
    if candle.low > candle.open or candle.low > candle.close:
        raise InvalidMarketDataError(
            f"Candle low above open/close for {candle.symbol} @ {candle.open_time}"
        )
    if candle.volume is not None and candle.volume < 0:
        raise InvalidMarketDataError(
            f"Candle volume must not be negative for {candle.symbol} @ {candle.open_time}"
        )
    if candle.close_time is not None and candle.close_time <= candle.open_time:
        raise InvalidMarketDataError(
            f"Candle close_time must be after open_time for {candle.symbol} @ {candle.open_time}"
        )
    return candle


def dedupe_candles(candles: list[Candle]) -> list[Candle]:
    """De-duplicate by (symbol, timeframe, open_time), keeping the last seen.

    Input ordering is preserved by open_time ascending.
    """
    keyed: dict[tuple[str, str, object], Candle] = {}
    for candle in candles:
        keyed[(candle.symbol, candle.timeframe.value, candle.open_time)] = candle
    return sorted(keyed.values(), key=lambda item: item.open_time)
