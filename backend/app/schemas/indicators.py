"""Indicator API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.market.indicators.base import (
    ATRResult,
    BollingerBandsResult,
    EMAResult,
    MACDResult,
    RSIResult,
    SMAResult,
    VolumeAnalysisResult,
)
from app.market.services.indicator_service import IndicatorBundle


class _Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IndicatorPointSchema(_Schema):
    timestamp: datetime | None
    value: float


class SeriesSchema(_Schema):
    period: int
    latest: float | None
    values: list[IndicatorPointSchema]

    @classmethod
    def from_series(cls, result: SMAResult | EMAResult | RSIResult | ATRResult) -> SeriesSchema:
        return cls(
            period=result.period,
            latest=result.latest,
            values=[IndicatorPointSchema.model_validate(point) for point in result.values],
        )


class MACDSchema(_Schema):
    fast_period: int
    slow_period: int
    signal_period: int
    latest_macd: float | None
    latest_signal: float | None
    latest_histogram: float | None
    macd: list[IndicatorPointSchema]
    signal: list[IndicatorPointSchema]
    histogram: list[IndicatorPointSchema]

    @classmethod
    def from_domain(cls, result: MACDResult) -> MACDSchema:
        return cls(**result.model_dump())


class BollingerSchema(_Schema):
    period: int
    std_dev: float
    latest_middle: float | None
    latest_upper: float | None
    latest_lower: float | None
    latest_bandwidth: float | None
    latest_percent_b: float | None
    middle: list[IndicatorPointSchema]
    upper: list[IndicatorPointSchema]
    lower: list[IndicatorPointSchema]
    bandwidth: list[IndicatorPointSchema]
    percent_b: list[IndicatorPointSchema]

    @classmethod
    def from_domain(cls, result: BollingerBandsResult) -> BollingerSchema:
        return cls(**result.model_dump())


class VolumeSchema(_Schema):
    ma_period: int
    current_volume: float | None
    average_volume: float | None
    relative_volume: float | None
    volume_change_pct: float | None
    series: list[IndicatorPointSchema]

    @classmethod
    def from_domain(cls, result: VolumeAnalysisResult) -> VolumeSchema:
        return cls(**result.model_dump())


class IndicatorResponseSchema(_Schema):
    symbol: str | None
    timeframe: str | None
    price: float | None
    data_timestamp: datetime | None
    calculated_at: datetime
    age_seconds: float | None
    is_stale: bool | None
    sma: SeriesSchema
    ema: SeriesSchema
    rsi: SeriesSchema
    macd: MACDSchema
    atr: SeriesSchema
    bollinger: BollingerSchema
    volume: VolumeSchema

    @classmethod
    def from_bundle(
        cls, bundle: IndicatorBundle, *, age_seconds: float | None, is_stale: bool | None
    ) -> IndicatorResponseSchema:
        return cls(
            symbol=bundle.symbol,
            timeframe=bundle.timeframe,
            price=bundle.price,
            data_timestamp=bundle.data_timestamp,
            calculated_at=bundle.calculated_at,
            age_seconds=age_seconds,
            is_stale=is_stale,
            sma=SeriesSchema.from_series(bundle.sma),
            ema=SeriesSchema.from_series(bundle.ema),
            rsi=SeriesSchema.from_series(bundle.rsi),
            macd=MACDSchema.from_domain(bundle.macd),
            atr=SeriesSchema.from_series(bundle.atr),
            bollinger=BollingerSchema.from_domain(bundle.bollinger),
            volume=VolumeSchema.from_domain(bundle.volume),
        )
