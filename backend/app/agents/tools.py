"""Agent tool layer.

Read-only market/strategy/portfolio/risk tools plus exactly one write-capable
tool: ``create_trade_proposal``. There is deliberately no execution tool.

Portfolio/risk/proposal services are imported lazily inside the tool methods so
importing :mod:`app.agents` never pulls broker/order/risk modules — the
architecture boundary is enforced at import time.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.enums import AgentRunMode
from app.ai.types import LLMToolSpec
from app.core.config import Settings, get_settings
from app.core.exceptions import AegisError, ValidationError
from app.core.logging import get_logger
from app.market.enums import Timeframe
from app.market.indicators import atr, bollinger, ema, last_value, macd, rsi
from app.market.services.market_data import MarketDataService
from app.market.validation import normalize_symbol
from app.models.user import User
from app.repositories.strategy import StrategySignalRepository
from app.strategies.regime import MarketRegimeService

logger = get_logger(__name__)

READ_TOOLS = (
    "get_market_context",
    "get_quote",
    "get_candles",
    "get_indicators",
    "get_market_regime",
    "get_strategy_signals",
    "get_portfolio",
    "get_positions",
    "get_risk_status",
    "get_recent_trades",
    "get_recent_proposals",
)
WRITE_TOOLS = ("create_trade_proposal",)
# Tools that must never exist on the agent (defence in depth for tests).
FORBIDDEN_TOOLS = (
    "submit_order",
    "execute_proposal",
    "cancel_order",
    "change_risk_settings",
    "pause_trading",
    "resume_trading",
    "emergency_stop",
    "broker_buy",
    "broker_sell",
)


@dataclass
class AgentToolContext:
    session: AsyncSession
    user: User
    symbol: str
    timeframe: str
    mode: AgentRunMode
    settings: Settings

    def market(self) -> MarketDataService:
        return MarketDataService(self.session, settings=self.settings)


def _spec(name: str, description: str, properties: dict, required: list[str]) -> LLMToolSpec:
    return LLMToolSpec(
        name=name,
        description=description,
        parameters={
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    )


_STRING = {"type": "string"}


class AgentToolRegistry:
    def __init__(self, context: AgentToolContext) -> None:
        self._ctx = context

    # --- specs --------------------------------------------------------------
    def specs(self) -> list[LLMToolSpec]:
        specs = [
            _spec(
                "get_market_context",
                "Snapshot for the target asset: quote, regime and indicator summary.",
                {},
                [],
            ),
            _spec("get_quote", "Latest quote for a symbol.", {"symbol": _STRING}, ["symbol"]),
            _spec(
                "get_candles",
                "Recent OHLCV candles.",
                {"symbol": _STRING, "timeframe": _STRING, "limit": {"type": "integer"}},
                ["symbol"],
            ),
            _spec(
                "get_indicators",
                "Technical indicators (EMA, RSI, MACD, ATR, Bollinger %B).",
                {"symbol": _STRING, "timeframe": _STRING},
                ["symbol"],
            ),
            _spec(
                "get_market_regime",
                "Deterministic market regime (trend + volatility).",
                {"symbol": _STRING, "timeframe": _STRING},
                ["symbol"],
            ),
            _spec(
                "get_strategy_signals",
                "Recent deterministic StrategySignals.",
                {"symbol": _STRING, "limit": {"type": "integer"}},
                [],
            ),
            _spec("get_portfolio", "Portfolio summary (equity, cash, exposure).", {}, []),
            _spec("get_positions", "Open positions.", {}, []),
            _spec("get_risk_status", "Risk limits, exposure and trading state.", {}, []),
            _spec(
                "get_recent_trades",
                "Recent completed trades.",
                {"limit": {"type": "integer"}},
                [],
            ),
            _spec(
                "get_recent_proposals",
                "Recent trade proposals.",
                {"limit": {"type": "integer"}},
                [],
            ),
        ]
        if self._ctx.mode is AgentRunMode.PROPOSE:
            specs.append(
                _spec(
                    "create_trade_proposal",
                    "Create exactly one DRAFT trade proposal. Does not execute or place orders.",
                    {
                        "symbol": _STRING,
                        "side": _STRING,
                        "order_type": _STRING,
                        "quantity": {"type": "number"},
                        "notional": {"type": "number"},
                        "limit_price": {"type": "number"},
                        "stop_price": {"type": "number"},
                        "stop_loss": {"type": "number"},
                        "take_profit": {"type": "number"},
                        "strategy_signal_id": _STRING,
                        "confidence": {"type": "number"},
                        "summary": _STRING,
                    },
                    ["symbol", "side"],
                )
            )
        return specs

    # --- execution ----------------------------------------------------------
    async def execute(
        self, name: str, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> tuple[bool, dict, str]:
        if name in FORBIDDEN_TOOLS or name not in (*READ_TOOLS, *WRITE_TOOLS):
            return False, {"error": "tool_not_available"}, f"tool {name} is not available"
        if name == "create_trade_proposal" and self._ctx.mode is not AgentRunMode.PROPOSE:
            return (
                False,
                {"error": "proposal_not_permitted"},
                "proposals are not permitted in this mode",
            )
        handler = getattr(self, f"_tool_{name}")
        try:
            payload = await handler(arguments, idempotency_key=idempotency_key)
            return True, payload, _summarise(name, payload)
        except AegisError as exc:
            return (
                False,
                {"error": exc.code, "message": exc.message},
                f"{name} failed: {exc.message}",
            )
        except Exception:  # noqa: BLE001 - never leak internals to the model
            logger.warning("agent_tool_failed", tool=name)
            return False, {"error": "tool_error"}, f"{name} failed"

    # --- read tools ---------------------------------------------------------
    async def _tool_get_market_context(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        symbol = self._symbol(args.get("symbol") or self._ctx.symbol)
        timeframe = self._timeframe(args.get("timeframe") or self._ctx.timeframe)
        quote = await self._ctx.market().get_quote(symbol)
        candles = await self._ctx.market().get_latest_candles(symbol, timeframe, 120)
        regime = MarketRegimeService(self._ctx.settings).classify(candles)
        return {
            "symbol": symbol,
            "timeframe": timeframe.value,
            "quote": _quote_dict(quote),
            "regime": {
                "primary": regime.primary.value,
                "trend": regime.trend.value,
                "volatility": regime.volatility.value,
                "metrics": regime.metrics,
            },
            "indicators": _indicator_dict(candles),
        }

    async def _tool_get_quote(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        symbol = self._symbol(args["symbol"])
        return _quote_dict(await self._ctx.market().get_quote(symbol))

    async def _tool_get_candles(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        symbol = self._symbol(args["symbol"])
        timeframe = self._timeframe(args.get("timeframe") or self._ctx.timeframe)
        limit = min(max(int(args.get("limit") or 60), 5), 200)
        candles = await self._ctx.market().get_latest_candles(symbol, timeframe, limit)
        return {
            "symbol": symbol,
            "timeframe": timeframe.value,
            "candles": [
                {
                    "time": (candle.close_time or candle.open_time).isoformat(),
                    "open": str(candle.open),
                    "high": str(candle.high),
                    "low": str(candle.low),
                    "close": str(candle.close),
                    "volume": candle.volume,
                }
                for candle in candles
            ],
        }

    async def _tool_get_indicators(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        symbol = self._symbol(args["symbol"])
        timeframe = self._timeframe(args.get("timeframe") or self._ctx.timeframe)
        candles = await self._ctx.market().get_latest_candles(symbol, timeframe, 120)
        return {
            "symbol": symbol,
            "timeframe": timeframe.value,
            "indicators": _indicator_dict(candles),
        }

    async def _tool_get_market_regime(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        symbol = self._symbol(args["symbol"])
        timeframe = self._timeframe(args.get("timeframe") or self._ctx.timeframe)
        candles = await self._ctx.market().get_latest_candles(symbol, timeframe, 120)
        regime = MarketRegimeService(self._ctx.settings).classify(candles)
        return {
            "symbol": symbol,
            "trend": regime.trend.value,
            "volatility": regime.volatility.value,
            "primary": regime.primary.value,
            "metrics": regime.metrics,
        }

    async def _tool_get_strategy_signals(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        symbol = args.get("symbol")
        limit = min(max(int(args.get("limit") or 10), 1), 25)
        rows = await StrategySignalRepository(self._ctx.session).list_signals(
            symbol=self._symbol(symbol) if symbol else None, limit=limit
        )
        return {
            "signals": [
                {
                    "id": str(row.id),
                    "symbol": row.symbol,
                    "strategy_id": str(row.strategy_id),
                    "direction": row.direction.value,
                    "strength": str(row.strength),
                    "confidence": str(row.confidence),
                    "timeframe": row.timeframe,
                    "market_regime": row.market_regime.value if row.market_regime else None,
                    "signal_time": row.signal_time.isoformat(),
                    "indicators": row.indicators or {},
                }
                for row in rows
            ]
        }

    async def _tool_get_portfolio(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        service = await self._portfolio_service()
        summary = await service.summary()
        return {
            "currency": summary.currency,
            "equity": str(summary.equity),
            "cash": str(summary.cash),
            "buying_power": str(summary.buying_power),
            "exposure_percent": str(summary.exposure_percent),
            "position_count": summary.position_count,
            "daily_pnl": str(summary.daily_pnl) if summary.daily_pnl is not None else None,
        }

    async def _tool_get_positions(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        service = await self._portfolio_service()
        positions = await service.positions()
        return {
            "positions": [
                {
                    "symbol": position.symbol,
                    "quantity": str(position.quantity),
                    "average_entry_price": str(position.average_entry_price),
                    "current_price": str(position.current_price)
                    if position.current_price is not None
                    else None,
                    "market_value": str(position.market_value),
                    "unrealized_pnl": str(position.unrealized_pnl),
                    "weight_percent": str(position.weight_percent),
                }
                for position in positions
            ]
        }

    async def _tool_get_risk_status(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        from app.risk.settings_service import RiskSettingsService
        from app.risk.trading_state import TradingStateService

        service = await self._portfolio_service()
        summary = await service.summary()
        limits = await RiskSettingsService(self._ctx.session, self._ctx.settings).get_or_create(
            self._ctx.user.id
        )
        state = await TradingStateService(
            self._ctx.session, settings=self._ctx.settings
        ).get_or_create()
        return {
            "trading_state": state.trading_state.value,
            "portfolio_exposure_percent": str(summary.exposure_percent),
            "max_portfolio_exposure_percent": str(limits.max_portfolio_exposure_percent),
            "open_positions": summary.position_count,
            "max_open_positions": limits.max_open_positions,
            "max_position_percent": str(limits.max_position_percent),
            "require_stop_loss": limits.require_stop_loss,
            "min_confidence": str(limits.min_strategy_confidence),
        }

    async def _tool_get_recent_trades(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        from sqlalchemy import select

        from app.brokers.bootstrap import ensure_paper_account
        from app.models.order import Trade

        _, portfolio = await ensure_paper_account(
            self._ctx.session, self._ctx.user, self._ctx.settings
        )
        limit = min(max(int(args.get("limit") or 10), 1), 25)
        rows = (
            await self._ctx.session.execute(
                select(Trade)
                .where(Trade.portfolio_id == portfolio.id)
                .order_by(Trade.opened_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return {
            "trades": [
                {
                    "symbol": row.symbol,
                    "side": row.side.value,
                    "quantity": str(row.quantity),
                    "entry_price": str(row.entry_price),
                    "exit_price": str(row.exit_price) if row.exit_price is not None else None,
                    "pnl": str(row.pnl),
                    "opened_at": row.opened_at.isoformat(),
                    "closed_at": row.closed_at.isoformat() if row.closed_at else None,
                }
                for row in rows
            ]
        }

    async def _tool_get_recent_proposals(self, args: dict, *, idempotency_key=None) -> dict:  # noqa: ANN001
        from app.brokers.bootstrap import ensure_paper_account
        from app.repositories.proposal import TradeProposalRepository

        _, portfolio = await ensure_paper_account(
            self._ctx.session, self._ctx.user, self._ctx.settings
        )
        limit = min(max(int(args.get("limit") or 10), 1), 25)
        rows = await TradeProposalRepository(self._ctx.session).list_for_portfolio(
            portfolio.id, limit=limit
        )
        return {
            "proposals": [
                {
                    "id": str(row.id),
                    "symbol": row.symbol,
                    "action": row.action.value,
                    "status": row.status.value,
                    "confidence": str(row.confidence),
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        }

    # --- write tool ---------------------------------------------------------
    async def _tool_create_trade_proposal(  # noqa: ANN001
        self, args: dict, *, idempotency_key: str | None = None
    ) -> dict:
        from app.models.enums import OrderType, ProposalSource, TradeSide
        from app.proposals.service import ProposalService
        from app.proposals.types import ProposalCreate

        symbol = self._symbol(args.get("symbol") or self._ctx.symbol)
        side = str(args.get("side", "")).upper()
        if side not in ("BUY", "SELL"):
            raise ValidationError("side must be BUY or SELL")
        order_type = str(args.get("order_type") or "MARKET").upper()
        if order_type not in {member.value for member in OrderType}:
            raise ValidationError("unsupported order_type")

        payload = ProposalCreate(
            symbol=symbol,
            side=TradeSide(side),
            order_type=OrderType(order_type),
            quantity=_decimal(args.get("quantity")),
            notional=_decimal(args.get("notional")),
            limit_price=_decimal(args.get("limit_price")),
            stop_price=_decimal(args.get("stop_price")),
            stop_loss=_decimal(args.get("stop_loss")),
            take_profit=_decimal(args.get("take_profit")),
            strategy_signal_id=_uuid(args.get("strategy_signal_id")),
            confidence=_decimal(args.get("confidence")) or Decimal("0.5"),
            reasoning_summary=(str(args.get("summary"))[:1000] if args.get("summary") else None),
            idempotency_key=idempotency_key,
        )
        proposal = await ProposalService(
            self._ctx.session,
            self._ctx.market(),
            self._ctx.user,
            settings=self._ctx.settings,
        ).create(payload, source=ProposalSource.AGENT)
        return {
            "proposal_id": str(proposal.id),
            "status": proposal.status.value,
            "symbol": proposal.symbol,
            "note": "DRAFT proposal only; it still requires risk evaluation and manual execution.",
        }

    # --- helpers ------------------------------------------------------------
    async def _portfolio_service(self):  # noqa: ANN202
        from app.brokers.bootstrap import ensure_paper_account
        from app.portfolio.service import PortfolioService

        account, portfolio = await ensure_paper_account(
            self._ctx.session, self._ctx.user, self._ctx.settings
        )
        return PortfolioService(
            self._ctx.session,
            portfolio,
            self._ctx.market(),
            account=account,
            settings=self._ctx.settings,
        )

    def _symbol(self, value: str | None) -> str:
        return normalize_symbol(value or self._ctx.symbol)

    def _timeframe(self, value: str | None) -> Timeframe:
        return Timeframe.parse(value or self._ctx.timeframe)


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value))
    except Exception as exc:  # noqa: BLE001
        raise ValidationError("numeric argument is invalid") from exc
    return parsed if parsed > 0 else None


def _uuid(value: Any) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise ValidationError("strategy_signal_id is invalid") from exc


def _quote_dict(quote) -> dict:  # noqa: ANN001
    return {
        "symbol": quote.symbol,
        "last": str(quote.last),
        "bid": str(quote.bid) if quote.bid is not None else None,
        "ask": str(quote.ask) if quote.ask is not None else None,
        "previous_close": str(quote.previous_close) if quote.previous_close is not None else None,
        "volume": quote.volume,
        "market_timestamp": quote.market_timestamp.isoformat(),
    }


def _indicator_dict(candles) -> dict:  # noqa: ANN001
    if not candles:
        return {}
    closes = [float(candle.close) for candle in candles]
    highs = [float(candle.high) for candle in candles]
    lows = [float(candle.low) for candle in candles]
    _, _, _, _, percent_b = bollinger(closes, 20, 2.0)
    macd_line, signal_line, histogram = macd(closes, 12, 26, 9)
    return {
        "ema_fast": _round(last_value(ema(closes, 20))),
        "ema_slow": _round(last_value(ema(closes, 50))),
        "rsi": _round(last_value(rsi(closes, 14))),
        "macd": _round(last_value(macd_line)),
        "macd_signal": _round(last_value(signal_line)),
        "macd_histogram": _round(last_value(histogram)),
        "atr": _round(last_value(atr(highs, lows, closes, 14))),
        "percent_b": _round(last_value(percent_b)),
        "price": _round(float(candles[-1].close)),
    }


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _summarise(name: str, payload: dict) -> str:
    if name == "create_trade_proposal":
        return f"proposal {payload.get('proposal_id')} created ({payload.get('status')})"
    if "signals" in payload:
        return f"{len(payload['signals'])} signals"
    if "positions" in payload:
        return f"{len(payload['positions'])} positions"
    if "trades" in payload:
        return f"{len(payload['trades'])} trades"
    if "proposals" in payload:
        return f"{len(payload['proposals'])} proposals"
    return "ok"


def utc_now() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)


def effective_settings(settings: Settings | None = None) -> Settings:
    return settings or get_settings()
