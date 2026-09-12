"""Indicator service: turns candles into typed indicator results.

Consumed later by the Strategy Engine, backtester and agent tools. It has no
dependency on those modules, FastAPI, SQLAlchemy or provider SDKs.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

from app.market.domain.models import Candle
from app.market.indicators.atr import atr
from app.market.indicators.base import (
    ATRResult,
    BollingerBandsResult,
    EMAResult,
    MACDResult,
    RSIResult,
    SMAResult,
    VolumeAnalysisResult,
    last_value,
    points,
)
from app.market.indicators.bollinger import bollinger
from app.market.indicators.ema import ema
from app.market.indicators.macd import macd
from app.market.indicators.rsi import rsi
from app.market.indicators.sma import sma
from app.market.indicators.volume import volume_analysis


class IndicatorConfig(BaseModel):
    """Configurable indicator windows (conventional defaults)."""

    sma_period: int = Field(default=20, gt=0)
    ema_period: int = Field(default=20, gt=0)
    rsi_period: int = Field(default=14, gt=0)
    macd_fast: int = Field(default=12, gt=0)
    macd_slow: int = Field(default=26, gt=0)
    macd_signal: int = Field(default=9, gt=0)
    atr_period: int = Field(default=14, gt=0)
    bollinger_period: int = Field(default=20, gt=0)
    bollinger_std: float = Field(default=2.0, gt=0)
    volume_period: int = Field(default=20, gt=0)

    @model_validator(mode="after")
    def _macd_order(self) -> IndicatorConfig:
        if self.macd_fast >= self.macd_slow:
            raise ValueError("macd_fast must be less than macd_slow")
        return self


class IndicatorBundle(BaseModel):
    symbol: str | None
    timeframe: str | None
    price: float | None
    data_timestamp: datetime | None
    calculated_at: datetime
    sma: SMAResult
    ema: EMAResult
    rsi: RSIResult
    macd: MACDResult
    atr: ATRResult
    bollinger: BollingerBandsResult
    volume: VolumeAnalysisResult


class IndicatorService:
    def __init__(
        self,
        config: IndicatorConfig | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = config or IndicatorConfig()
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def config(self) -> IndicatorConfig:
        return self._config

    # --- individual indicators ---------------------------------------------
    def calculate_sma(self, candles: Sequence[Candle], period: int | None = None) -> SMAResult:
        window = period or self._config.sma_period
        closes = _closes(candles)
        values = sma(closes, window)
        return SMAResult(
            period=window, values=points(_times(candles), values), latest=last_value(values)
        )

    def calculate_ema(self, candles: Sequence[Candle], period: int | None = None) -> EMAResult:
        window = period or self._config.ema_period
        values = ema(_closes(candles), window)
        return EMAResult(
            period=window, values=points(_times(candles), values), latest=last_value(values)
        )

    def calculate_rsi(self, candles: Sequence[Candle], period: int | None = None) -> RSIResult:
        window = period or self._config.rsi_period
        values = rsi(_closes(candles), window)
        return RSIResult(
            period=window, values=points(_times(candles), values), latest=last_value(values)
        )

    def calculate_macd(
        self,
        candles: Sequence[Candle],
        fast: int | None = None,
        slow: int | None = None,
        signal: int | None = None,
    ) -> MACDResult:
        fast = fast or self._config.macd_fast
        slow = slow or self._config.macd_slow
        signal = signal or self._config.macd_signal
        macd_line, signal_line, histogram = macd(_closes(candles), fast, slow, signal)
        times = _times(candles)
        return MACDResult(
            fast_period=fast,
            slow_period=slow,
            signal_period=signal,
            macd=points(times, macd_line),
            signal=points(times, signal_line),
            histogram=points(times, histogram),
            latest_macd=last_value(macd_line),
            latest_signal=last_value(signal_line),
            latest_histogram=last_value(histogram),
        )

    def calculate_atr(self, candles: Sequence[Candle], period: int | None = None) -> ATRResult:
        window = period or self._config.atr_period
        highs = _floats(candles, "high")
        lows = _floats(candles, "low")
        closes = _closes(candles)
        values = atr(highs, lows, closes, window)
        return ATRResult(
            period=window, values=points(_times(candles), values), latest=last_value(values)
        )

    def calculate_bollinger(
        self, candles: Sequence[Candle], period: int | None = None, num_std: float | None = None
    ) -> BollingerBandsResult:
        window = period or self._config.bollinger_period
        std = num_std if num_std is not None else self._config.bollinger_std
        middle, upper, lower, bandwidth, percent_b = bollinger(_closes(candles), window, std)
        times = _times(candles)
        return BollingerBandsResult(
            period=window,
            std_dev=std,
            middle=points(times, middle),
            upper=points(times, upper),
            lower=points(times, lower),
            bandwidth=points(times, bandwidth),
            percent_b=points(times, percent_b),
            latest_middle=last_value(middle),
            latest_upper=last_value(upper),
            latest_lower=last_value(lower),
            latest_bandwidth=last_value(bandwidth),
            latest_percent_b=last_value(percent_b),
        )

    def calculate_volume(
        self, candles: Sequence[Candle], period: int | None = None
    ) -> VolumeAnalysisResult:
        window = period or self._config.volume_period
        stats = volume_analysis([candle.volume or 0 for candle in candles], window)
        return VolumeAnalysisResult(
            ma_period=window,
            current_volume=stats.current_volume,
            average_volume=stats.average_volume,
            relative_volume=stats.relative_volume,
            volume_change_pct=stats.volume_change_pct,
            series=points(_times(candles), stats.moving_average),
        )

    # --- bundle -------------------------------------------------------------
    def calculate_indicators(
        self, candles: Sequence[Candle], config: IndicatorConfig | None = None
    ) -> IndicatorBundle:
        cfg = config or self._config
        last = candles[-1] if candles else None
        return IndicatorBundle(
            symbol=last.symbol if last else None,
            timeframe=last.timeframe.value if last else None,
            price=float(last.close) if last else None,
            data_timestamp=(last.close_time or last.open_time) if last else None,
            calculated_at=self._clock().astimezone(UTC),
            sma=self.calculate_sma(candles, cfg.sma_period),
            ema=self.calculate_ema(candles, cfg.ema_period),
            rsi=self.calculate_rsi(candles, cfg.rsi_period),
            macd=self.calculate_macd(candles, cfg.macd_fast, cfg.macd_slow, cfg.macd_signal),
            atr=self.calculate_atr(candles, cfg.atr_period),
            bollinger=self.calculate_bollinger(candles, cfg.bollinger_period, cfg.bollinger_std),
            volume=self.calculate_volume(candles, cfg.volume_period),
        )


def _closes(candles: Sequence[Candle]) -> list[float]:
    return _floats(candles, "close")


def _floats(candles: Sequence[Candle], field: str) -> list[float]:
    return [float(getattr(candle, field)) for candle in candles]


def _times(candles: Sequence[Candle]) -> list[datetime | None]:
    return [candle.open_time for candle in candles]
