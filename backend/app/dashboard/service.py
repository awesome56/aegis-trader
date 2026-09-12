"""Dashboard composition.

Aggregates portfolio, broker, market and notification state into a single
response so clients do not need N requests. Unimplemented domains (agent, risk,
strategies, backtesting) are reported as unavailable rather than faked.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.bootstrap import ensure_paper_account
from app.brokers.types import BrokerStatus
from app.core.config import Settings, get_settings
from app.market.providers.factory import get_market_data_provider
from app.market.services.market_data import MarketDataService
from app.models.user import User
from app.portfolio.service import PortfolioService
from app.realtime.publisher import get_connection_manager
from app.repositories.notification import NotificationRepository
from app.repositories.order import OrderRepository
from app.schemas.broker import BrokerOrderSchema
from app.schemas.dashboard import DashboardAvailability, DashboardSchema
from app.schemas.notifications import NotificationSchema

RECENT_LIMIT = 5


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

        market_status = await self._market.get_market_status()
        try:
            provider_health = await get_market_data_provider(self._settings).health_check()
            market_data_status = provider_health.status.value
        except Exception:  # noqa: BLE001 - status must never break the dashboard
            market_data_status = "UNKNOWN"

        return DashboardSchema(
            portfolio=summary,
            trading_mode=self._settings.TRADING_MODE,
            broker_provider=self._settings.BROKER_PROVIDER,
            broker_status=BrokerStatus.PAPER.value,
            market_data_provider=self._settings.MARKET_DATA_PROVIDER,
            market_data_status=market_data_status,
            market_is_open=market_status.is_open,
            market_session=market_status.session.value,
            realtime_connections=get_connection_manager().connection_count,
            unread_notifications=unread,
            drawdown_percent=drawdown,
            recent_orders=[BrokerOrderSchema.from_model(order) for order in orders],
            recent_notifications=[
                NotificationSchema.from_model(notification) for notification in notifications
            ],
            availability=DashboardAvailability(),
        )
