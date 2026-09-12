"""Per-user risk settings: env-seeded defaults + persisted overrides."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.risk import RiskSettings
from app.repositories.risk import RiskSettingsRepository
from app.risk.types import RiskLimitsSnapshot

_MAX_TO_DECIMAL_FIELDS = (
    "max_position_percent",
    "max_portfolio_exposure_percent",
    "max_daily_loss_percent",
    "max_drawdown_percent",
    "max_risk_per_trade_percent",
    "min_strategy_confidence",
    "min_reward_risk_ratio",
    "max_sector_exposure_percent",
    "max_asset_class_exposure_percent",
    "commission_buffer_bps",
)


class RiskSettingsService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._repo = RiskSettingsRepository(session)

    def env_defaults(self) -> RiskLimitsSnapshot:
        s = self._settings
        return RiskLimitsSnapshot(
            is_enabled=s.RISK_ENABLED,
            max_position_percent=Decimal(str(s.MAX_POSITION_PERCENTAGE)),
            max_portfolio_exposure_percent=Decimal(str(s.MAX_PORTFOLIO_EXPOSURE)),
            max_open_positions=s.MAX_OPEN_POSITIONS,
            max_daily_loss_percent=Decimal(str(s.MAX_DAILY_LOSS_PERCENTAGE)),
            max_drawdown_percent=Decimal(str(s.MAX_DRAWDOWN_PERCENTAGE)),
            max_trades_per_day=s.MAX_TRADES_PER_DAY,
            max_risk_per_trade_percent=Decimal(str(s.RISK_MAX_RISK_PER_TRADE_PERCENT)),
            min_strategy_confidence=Decimal(str(s.MINIMUM_CONFIDENCE)),
            min_reward_risk_ratio=Decimal(str(s.MINIMUM_RISK_REWARD_RATIO)),
            require_stop_loss=s.REQUIRE_STOP_LOSS,
            require_strategy_signal=s.RISK_REQUIRE_STRATEGY_SIGNAL,
            max_sector_exposure_percent=Decimal(str(s.MAX_SECTOR_EXPOSURE)),
            max_asset_class_exposure_percent=Decimal(str(s.MAX_ASSET_CLASS_EXPOSURE)),
            unknown_sector_policy=s.RISK_UNKNOWN_SECTOR_POLICY,
            daily_loss_include_unrealized=s.RISK_DAILY_LOSS_INCLUDE_UNREALIZED,
            commission_buffer_bps=Decimal(str(s.RISK_COMMISSION_BUFFER_BPS)),
        )

    async def get_or_create(self, user_id: uuid.UUID) -> RiskSettings:
        existing = await self._repo.get_for_user(user_id)
        if existing is not None:
            return existing
        defaults = self.env_defaults()
        row = RiskSettings(
            user_id=user_id,
            is_enabled=defaults.is_enabled,
            max_position_percent=defaults.max_position_percent,
            max_portfolio_exposure_percent=defaults.max_portfolio_exposure_percent,
            max_open_positions=defaults.max_open_positions,
            max_daily_loss_percent=defaults.max_daily_loss_percent,
            max_drawdown_percent=defaults.max_drawdown_percent,
            max_trades_per_day=defaults.max_trades_per_day,
            max_risk_per_trade_percent=defaults.max_risk_per_trade_percent,
            min_strategy_confidence=defaults.min_strategy_confidence,
            min_reward_risk_ratio=defaults.min_reward_risk_ratio,
            require_stop_loss=defaults.require_stop_loss,
            require_strategy_signal=defaults.require_strategy_signal,
            max_sector_exposure_percent=defaults.max_sector_exposure_percent,
            max_asset_class_exposure_percent=defaults.max_asset_class_exposure_percent,
            unknown_sector_policy=defaults.unknown_sector_policy,
            daily_loss_include_unrealized=defaults.daily_loss_include_unrealized,
            commission_buffer_bps=defaults.commission_buffer_bps,
        )
        return await self._repo.add(row)

    def to_snapshot(self, row: RiskSettings) -> RiskLimitsSnapshot:
        return RiskLimitsSnapshot(
            is_enabled=row.is_enabled,
            max_position_percent=Decimal(str(row.max_position_percent)),
            max_portfolio_exposure_percent=Decimal(str(row.max_portfolio_exposure_percent)),
            max_open_positions=row.max_open_positions,
            max_daily_loss_percent=Decimal(str(row.max_daily_loss_percent)),
            max_drawdown_percent=Decimal(str(row.max_drawdown_percent)),
            max_trades_per_day=row.max_trades_per_day,
            max_risk_per_trade_percent=Decimal(str(row.max_risk_per_trade_percent)),
            min_strategy_confidence=Decimal(str(row.min_strategy_confidence)),
            min_reward_risk_ratio=Decimal(str(row.min_reward_risk_ratio)),
            require_stop_loss=row.require_stop_loss,
            require_strategy_signal=row.require_strategy_signal,
            max_sector_exposure_percent=Decimal(str(row.max_sector_exposure_percent)),
            max_asset_class_exposure_percent=Decimal(str(row.max_asset_class_exposure_percent)),
            unknown_sector_policy=row.unknown_sector_policy,
            daily_loss_include_unrealized=row.daily_loss_include_unrealized,
            commission_buffer_bps=Decimal(str(row.commission_buffer_bps)),
        )

    async def update(self, row: RiskSettings, data: dict[str, object]) -> RiskSettings:
        for field, value in data.items():
            if value is None:
                continue
            if field in _MAX_TO_DECIMAL_FIELDS:
                setattr(row, field, Decimal(str(value)))
            else:
                setattr(row, field, value)
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return row
