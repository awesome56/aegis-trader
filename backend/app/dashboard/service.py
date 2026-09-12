"""Dashboard composition.

Aggregates portfolio, broker, market, risk, strategy and notification state into
a single response so clients do not need N requests. Unimplemented domains
(agent, backtesting) are reported as unavailable rather than faked.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.bootstrap import ensure_paper_account
from app.brokers.types import BrokerStatus
from app.core.config import Settings, get_settings
from app.market.providers.factory import get_market_data_provider
from app.market.services.market_data import MarketDataService
from app.models.strategy import Strategy
from app.models.user import User
from app.portfolio.service import PortfolioService
from app.realtime.publisher import get_connection_manager
from app.repositories.notification import NotificationRepository
from app.repositories.order import OrderRepository
from app.repositories.strategy import StrategyRepository, StrategySignalRepository
from app.risk.settings_service import RiskSettingsService
from app.risk.status import status_from_utilization_rows, utilization_rows
from app.risk.trading_state import TradingStateService
from app.schemas.broker import BrokerOrderSchema
from app.schemas.dashboard import DashboardAvailability, DashboardSchema
from app.schemas.notifications import NotificationSchema
from app.schemas.risk import RiskUtilizationSchema
from app.schemas.strategy import SignalSchema

RECENT_LIMIT = 5


def _signal_schema(signal, strategy: Strategy | None) -> SignalSchema:  # noqa: ANN001
    return SignalSchema(
        id=signal.id,
        strategy_id=signal.strategy_id,
        strategy_key=strategy.slug if strategy else None,
        strategy_name=strategy.name if strategy else None,
        symbol=signal.symbol,
        direction=signal.direction,
        strength=signal.strength,
        confidence=signal.confidence,
        price=signal.price,
        timeframe=signal.timeframe,
        time_horizon=signal.time_horizon,
        market_regime=signal.market_regime,
        indicators=signal.indicators,
        signal_time=signal.signal_time,
        data_timestamp=signal.data_timestamp,
        expires_at=signal.expires_at,
    )


class DashboardService:
    def __init__(
        self,
        session: AsyncSession,
        user: User,
        market: MarketDataService,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._user = user
        self._market = market
        self._settings = settings or get_settings()

    async def build(self) -> DashboardSchema:
        account, portfolio = await ensure_paper_account(self._session, self._user, self._settings)
        portfolio_service = PortfolioService(
            self._session, portfolio, self._market, account=account, settings=self._settings
        )
        summary = await portfolio_service.summary()
        drawdown = await portfolio_service.drawdown_percent()

        orders = await OrderRepository(self._session).list_for_account(
            account.id, limit=RECENT_LIMIT
        )
        notification_repo = NotificationRepository(self._session)
        notifications = await notification_repo.list_for_user(self._user.id, limit=RECENT_LIMIT)
        unread = await notification_repo.unread_count(self._user.id)

        trading_state_row = await TradingStateService(
            self._session, settings=self._settings
        ).get_or_create()
        limits = RiskSettingsService(self._session, self._settings)
        limits_snapshot = limits.to_snapshot(await limits.get_or_create(self._user.id))
        trades_today = await OrderRepository(self._session).count_created_since(
            account.id, datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        )
        risk_rows = utilization_rows(
            limits=limits_snapshot,
            equity=summary.equity,
            exposure_percent=summary.exposure_percent,
            open_positions=summary.position_count,
            trades_today=trades_today,
            drawdown_percent=drawdown,
            daily_pnl=summary.daily_pnl,
            warning=Decimal(str(self._settings.RISK_WARNING_UTILIZATION_PERCENT)),
            critical=Decimal(str(self._settings.RISK_CRITICAL_UTILIZATION_PERCENT)),
        )

        strategies = {item.id: item for item in await StrategyRepository(self._session).list_all()}
        recent_signals = await StrategySignalRepository(self._session).list_signals(
            limit=RECENT_LIMIT
        )

        market_status = await self._market.get_market_status()
        try:
            provider_health = await get_market_data_provider(self._settings).health_check()
            market_data_status = provider_health.status.value
        except Exception:  # noqa: BLE001 - status must never break the dashboard
            market_data_status = "UNKNOWN"

        return DashboardSchema(
            portfolio=summary,
            trading_mode=self._settings.TRADING_MODE,
            trading_state=trading_state_row.trading_state.value,
            broker_provider=self._settings.BROKER_PROVIDER,
            broker_status=BrokerStatus.PAPER.value,
            market_data_provider=self._settings.MARKET_DATA_PROVIDER,
            market_data_status=market_data_status,
            market_is_open=market_status.is_open,
            market_session=market_status.session.value,
            risk_status=status_from_utilization_rows(risk_rows).value,
            risk_utilizations=[RiskUtilizationSchema.model_validate(row) for row in risk_rows],
            recent_signals=[
                _signal_schema(signal, strategies.get(signal.strategy_id))
                for signal in recent_signals
            ],
            realtime_connections=get_connection_manager().connection_count,
            unread_notifications=unread,
            drawdown_percent=drawdown,
            recent_orders=[BrokerOrderSchema.from_model(order) for order in orders],
            recent_notifications=[
                NotificationSchema.from_model(notification) for notification in notifications
            ],
            availability=DashboardAvailability(),
        )
