"""Auto-trading policy service (Phase 10).

Enforces *may the agent act automatically?* (Demo and Live independently) and
exposes the action permissions used to gate dynamic agent tools. Financial
permission is still decided by the RiskEngine.
"""

from __future__ import annotations

import datetime as _dt
import uuid

from app.agents.enums import AgentRunMode
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.auto_trading import AutoTradingPolicy
from app.models.broker import BrokerAccount
from app.models.enums import AutoTradeAction, BrokerEnvironment, NotificationSeverity
from app.repositories.auto_trading import AutoTradingPolicyRepository
from app.repositories.broker_account import BrokerAccountRepository
from app.repositories.notification import SystemEventRepository
from sqlalchemy.ext.asyncio import AsyncSession

_ACTION_FIELD = {
    AutoTradeAction.OPEN: "allow_open",
    AutoTradeAction.ADD: "allow_add",
    AutoTradeAction.REDUCE: "allow_reduce",
    AutoTradeAction.CLOSE: "allow_close",
    AutoTradeAction.CANCEL_ORDER: "allow_cancel",
    AutoTradeAction.REPLACE_ORDER: "allow_replace",
}


class AutoTradingPolicyService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._policies = AutoTradingPolicyRepository(session)
        self._accounts = BrokerAccountRepository(session)

    async def get_or_create(
        self, user_id: uuid.UUID, account: BrokerAccount
    ) -> AutoTradingPolicy:
        policy = await self._policies.get_for_account(user_id, account.id)
        if policy is not None:
            return policy
        now = _dt.datetime.now(_dt.UTC)
        policy = AutoTradingPolicy(
            user_id=user_id,
            broker_account_id=account.id,
            environment=account.environment,
            enabled=False,
            allow_open=True,
            allow_add=False,
            allow_reduce=True,
            allow_close=True,
            allow_cancel=False,
            allow_replace=False,
            allow_manage_manual_positions=False,
            allow_manage_manual_orders=False,
            cooldown_seconds=0,
            created_at=now,
            updated_at=now,
        )
        await self._policies.add(policy)
        return policy

    async def get_for_account(
        self, user_id: uuid.UUID, account_id: uuid.UUID
    ) -> tuple[BrokerAccount, AutoTradingPolicy]:
        account = await self._accounts.get_for_user(account_id, user_id)
        if account is None:
            raise NotFoundError(f"Broker account {account_id} not found")
        return account, await self.get_or_create(user_id, account)

    async def update(self, policy: AutoTradingPolicy, **fields: object) -> AutoTradingPolicy:
        editable = {
            "allow_open",
            "allow_add",
            "allow_reduce",
            "allow_close",
            "allow_cancel",
            "allow_replace",
            "allow_manage_manual_positions",
            "allow_manage_manual_orders",
            "allowed_asset_classes",
            "allowed_symbols",
            "max_trade_notional",
            "max_position_notional",
            "max_trades_per_day",
            "cooldown_seconds",
            "min_agent_confidence",
            "require_strategy_signal",
            "min_strategy_confidence",
            "notes",
        }
        for key, value in fields.items():
            if key in editable and value is not None:
                setattr(policy, key, value)
        policy.updated_at = _dt.datetime.now(_dt.UTC)
        await self._session.flush()
        return policy

    async def enable(
        self,
        user_id: uuid.UUID,
        policy: AutoTradingPolicy,
        *,
        confirm: bool,
        phrase: str | None = None,
    ) -> AutoTradingPolicy:
        if not confirm:
            raise ValidationError("enabling auto trading requires confirm=true")
        if policy.environment is BrokerEnvironment.LIVE:
            if not self._settings.LIVE_TRADING_ALLOWED:
                raise ConflictError(
                    "live auto trading is disabled by the server (LIVE_TRADING_ALLOWED=false)"
                )
            if (phrase or "").strip() != self._settings.AUTO_TRADING_LIVE_CONFIRM_PHRASE:
                raise ValidationError("live activation confirmation phrase is incorrect")
        policy.enabled = True
        policy.updated_at = _dt.datetime.now(_dt.UTC)
        await self._session.flush()
        await self._audit(
            user_id,
            "auto_trading.enabled",
            policy,
            severity=(
                NotificationSeverity.CRITICAL
                if policy.environment is BrokerEnvironment.LIVE
                else NotificationSeverity.WARNING
            ),
        )
        return policy

    async def disable(
        self, user_id: uuid.UUID, policy: AutoTradingPolicy
    ) -> AutoTradingPolicy:
        policy.enabled = False
        policy.updated_at = _dt.datetime.now(_dt.UTC)
        await self._session.flush()
        await self._audit(user_id, "auto_trading.disabled", policy)
        return policy

    def allowed_actions(self, policy: AutoTradingPolicy | None) -> set[AutoTradeAction]:
        if policy is None or not policy.enabled:
            return set()
        return {
            action for action, field in _ACTION_FIELD.items() if getattr(policy, field, False)
        }

    def permits(
        self,
        policy: AutoTradingPolicy | None,
        action: AutoTradeAction,
        *,
        symbol: str | None = None,
        asset_class: str | None = None,
    ) -> tuple[bool, str | None]:
        if policy is None or not policy.enabled:
            return False, "AUTO_TRADING_DISABLED"
        if action not in self.allowed_actions(policy):
            return False, f"ACTION_NOT_PERMITTED:{action.value}"
        if asset_class and policy.allowed_asset_classes:
            if asset_class not in policy.allowed_asset_classes:
                return False, "ASSET_CLASS_NOT_ALLOWED"
        if symbol and policy.allowed_symbols:
            if symbol.upper() not in {str(s).upper() for s in policy.allowed_symbols}:
                return False, "SYMBOL_NOT_ALLOWED"
        return True, None

    def agent_mode(self, policy: AutoTradingPolicy | None) -> AgentRunMode:
        return AgentRunMode.PROPOSE if policy is None else AgentRunMode.PROPOSE

    async def _audit(
        self,
        user_id: uuid.UUID,
        event_type: str,
        policy: AutoTradingPolicy,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> None:
        await SystemEventRepository(self._session).record(
            event_type=event_type,
            source="auto_trading",
            message=f"Auto trading {event_type.split('.')[-1]} ({policy.environment.value})",
            severity=severity,
            actor=str(user_id),
            payload={
                "environment": policy.environment.value,
                "broker_account_id": str(policy.broker_account_id)
                if policy.broker_account_id
                else None,
            },
        )
