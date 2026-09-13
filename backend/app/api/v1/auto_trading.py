"""Auto-trading control API (Phase 10).

Demo and Live permissions are independent. Live activation additionally requires
the server `LIVE_TRADING_ALLOWED` interlock and an explicit phrase.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser, DbSession, get_current_user
from app.auto_trading.service import AutoTradingPolicyService
from app.core.config import get_settings
from app.models.auto_trading import AutoTradingPolicy
from app.models.enums import BrokerEnvironment
from app.repositories.broker_account import BrokerAccountRepository
from app.risk.trading_state import TradingStateService
from app.schemas.trading_control import (
    AutoTradingAccountStatus,
    AutoTradingEnableRequest,
    AutoTradingPolicySchema,
    AutoTradingPolicyUpdateRequest,
    AutoTradingStatusSchema,
)

router = APIRouter(
    prefix="/auto-trading", tags=["auto-trading"], dependencies=[Depends(get_current_user)]
)


def _policy_schema(policy: AutoTradingPolicy) -> AutoTradingPolicySchema:
    return AutoTradingPolicySchema(
        id=policy.id,
        broker_account_id=policy.broker_account_id,
        environment=policy.environment,
        enabled=policy.enabled,
        allow_open=policy.allow_open,
        allow_add=policy.allow_add,
        allow_reduce=policy.allow_reduce,
        allow_close=policy.allow_close,
        allow_cancel=policy.allow_cancel,
        allow_replace=policy.allow_replace,
        allow_manage_manual_positions=policy.allow_manage_manual_positions,
        allow_manage_manual_orders=policy.allow_manage_manual_orders,
        allowed_asset_classes=policy.allowed_asset_classes,
        allowed_symbols=policy.allowed_symbols,
        max_trade_notional=policy.max_trade_notional,  # type: ignore[arg-type]
        max_position_notional=policy.max_position_notional,  # type: ignore[arg-type]
        max_trades_per_day=policy.max_trades_per_day,
        cooldown_seconds=policy.cooldown_seconds,
        min_agent_confidence=policy.min_agent_confidence,  # type: ignore[arg-type]
        require_strategy_signal=policy.require_strategy_signal,
        min_strategy_confidence=policy.min_strategy_confidence,  # type: ignore[arg-type]
        notes=policy.notes,
    )


@router.get("/status", response_model=AutoTradingStatusSchema, summary="Auto-trading status")
async def status(session: DbSession, user: CurrentUser) -> AutoTradingStatusSchema:
    from app.brokers.bootstrap import ensure_paper_account

    service = AutoTradingPolicyService(session)
    state = await TradingStateService(session).get_or_create()
    await ensure_paper_account(session, user, get_settings())
    accounts = await BrokerAccountRepository(session).list_for_user(user.id)
    items: list[AutoTradingAccountStatus] = []
    for account in accounts:
        policy = await service.get_or_create(user.id, account)
        items.append(
            AutoTradingAccountStatus(
                broker_account_id=account.id,
                provider=account.broker,
                account_name=account.account_name,
                environment=account.environment,
                enabled=policy.enabled,
                trading_state=state.trading_state.value,
                policy=_policy_schema(policy),
            )
        )
    return AutoTradingStatusSchema(
        live_trading_allowed=get_settings().LIVE_TRADING_ALLOWED,
        demo_any_enabled=any(
            item.enabled and item.environment is BrokerEnvironment.DEMO for item in items
        ),
        live_any_enabled=any(
            item.enabled and item.environment is BrokerEnvironment.LIVE for item in items
        ),
        accounts=items,
    )


@router.get(
    "/{account_id}/policy", response_model=AutoTradingPolicySchema, summary="Get account policy"
)
async def get_policy(
    account_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> AutoTradingPolicySchema:
    _, policy = await AutoTradingPolicyService(session).get_for_account(user.id, account_id)
    return _policy_schema(policy)


@router.put(
    "/{account_id}/policy", response_model=AutoTradingPolicySchema, summary="Update account policy"
)
async def update_policy(
    account_id: uuid.UUID,
    payload: AutoTradingPolicyUpdateRequest,
    session: DbSession,
    user: CurrentUser,
) -> AutoTradingPolicySchema:
    service = AutoTradingPolicyService(session)
    _, policy = await service.get_for_account(user.id, account_id)
    policy = await service.update(policy, **payload.model_dump(exclude_unset=True))
    return _policy_schema(policy)


@router.post(
    "/{account_id}/enable", response_model=AutoTradingPolicySchema, summary="Enable auto trading"
)
async def enable(
    account_id: uuid.UUID,
    payload: AutoTradingEnableRequest,
    session: DbSession,
    user: CurrentUser,
) -> AutoTradingPolicySchema:
    service = AutoTradingPolicyService(session)
    _, policy = await service.get_for_account(user.id, account_id)
    policy = await service.enable(user.id, policy, confirm=payload.confirm, phrase=payload.phrase)
    return _policy_schema(policy)


@router.post(
    "/{account_id}/disable", response_model=AutoTradingPolicySchema, summary="Disable auto trading"
)
async def disable(
    account_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> AutoTradingPolicySchema:
    service = AutoTradingPolicyService(session)
    _, policy = await service.get_for_account(user.id, account_id)
    policy = await service.disable(user.id, policy)
    return _policy_schema(policy)
