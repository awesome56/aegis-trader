"""Application configuration loaded from environment variables.

All financial and risk values below are *conservative examples* intended to be
overridden per deployment. They are not financial advice.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TradingMode = Literal["paper", "live"]
Environment = Literal["development", "test", "staging", "production"]
KillSwitchState = Literal["TRADING_ENABLED", "TRADING_PAUSED", "TRADING_DISABLED", "EMERGENCY_STOP"]


class Settings(BaseSettings):
    """Strongly typed runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---------------------------------------------------------
    APP_NAME: str = "Aegis Trader"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Environment = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"]
    )

    # --- Database ------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://trader:trader@localhost:5432/trader"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Redis ---------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Auth / JWT ----------------------------------------------------------
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    PASSWORD_MIN_LENGTH: int = 12

    # --- Trading mode / live protection -------------------------------------
    TRADING_MODE: TradingMode = "paper"
    LIVE_TRADING_ENABLED: bool = False
    BROKER_LIVE_CREDENTIALS_PRESENT: bool = False
    MANUAL_LIVE_ACTIVATION: bool = False
    PAPER_INITIAL_BALANCE: float = 100_000.00

    # --- Broker --------------------------------------------------------------
    BROKER_PROVIDER: str = "paper"
    BROKER_PAPER_COMMISSION: float = 0.00
    BROKER_PAPER_SLIPPAGE_BPS: float = 2.0
    BROKER_PAPER_SPREAD_BPS: float = 1.0
    BROKER_PAPER_PARTIAL_FILLS: bool = False
    BROKER_PAPER_PARTIAL_FILL_RATIO: float = 0.5
    BROKER_PAPER_AUTO_CREATE_ACCOUNT: bool = True
    BROKER_PAPER_DEFAULT_CURRENCY: str = "USD"

    # --- Portfolio -----------------------------------------------------------
    PORTFOLIO_SNAPSHOT_INTERVAL_SECONDS: int = 300
    PORTFOLIO_HISTORY_MAX_POINTS: int = 1000

    # --- Realtime ------------------------------------------------------------
    WEBSOCKET_HEARTBEAT_SECONDS: int = 30

    # --- Execution / proposals (Phase 7) -------------------------------------
    TRADE_PROPOSAL_TTL_SECONDS: int = 300
    EXECUTION_MAX_PRICE_DEVIATION_BPS: float = 50.0
    EXECUTION_REQUIRE_FINAL_RISK_REVALIDATION: bool = True

    # --- Worker / scheduler (Track C) ----------------------------------------
    WORKER_ENABLED: bool = True
    WORKER_OPEN_ORDER_INTERVAL_SECONDS: int = 10
    WORKER_PORTFOLIO_SNAPSHOT_INTERVAL_SECONDS: int = 300
    WORKER_STRATEGY_EVALUATION_INTERVAL_SECONDS: int = 60
    WORKER_LOCK_TTL_SECONDS: int = 60
    WORKER_STRATEGY_SYMBOLS: str = ""  # comma-separated; falls back to MOCK_MARKET_SYMBOLS

    # --- Backtesting (Phase 8) ----------------------------------------------
    BACKTEST_ENABLED: bool = True
    BACKTEST_MAX_CONCURRENT_PER_USER: int = 2
    BACKTEST_MAX_CANDLES: int = 5000
    BACKTEST_MAX_RANGE_DAYS: int = 3650
    BACKTEST_DEFAULT_INITIAL_CAPITAL: float = 100000.0
    BACKTEST_DEFAULT_POSITION_PERCENT: float = 100.0
    BACKTEST_DEFAULT_COMMISSION_PCT: float = 0.0
    BACKTEST_DEFAULT_SLIPPAGE_PCT: float = 0.0
    BACKTEST_FORCE_CLOSE_AT_END: bool = True

    # --- Market data ---------------------------------------------------------
    MARKET_DATA_PROVIDER: str = "mock"
    # Legacy aliases (superseded by the explicit settings below; retained for
    # backward compatibility with existing deployments).
    MARKET_DATA_STALE_SECONDS: int = 60
    MARKET_DATA_CACHE_TTL_SECONDS: int = 5

    MARKET_CACHE_PREFIX: str = "market"
    MARKET_QUOTE_CACHE_TTL_SECONDS: int = 5
    MARKET_CANDLE_CACHE_TTL_SECONDS: int = 60
    MARKET_STATUS_CACHE_TTL_SECONDS: int = 30
    # Staleness thresholds are compared against the *market* timestamp, never the
    # time the backend received the data.
    MAX_QUOTE_AGE_SECONDS: int = 15
    MAX_INTRADAY_CANDLE_AGE_SECONDS: int = 300
    MAX_DAILY_CANDLE_AGE_SECONDS: int = 86400
    MARKET_MAX_CANDLE_LIMIT: int = 1000
    MARKET_DEFAULT_CURRENCY: str = "USD"
    # Active symbol universe for real providers (falls back to the mock list).
    MARKET_SYMBOLS: str = ""
    MARKET_HTTP_TIMEOUT_SECONDS: float = 15.0

    # Twelve Data (equities + forex + crypto)
    TWELVE_DATA_API_KEY: str = ""
    TWELVE_DATA_BASE_URL: str = "https://api.twelvedata.com"
    # Kraken public market data (crypto, keyless)
    KRAKEN_BASE_URL: str = "https://api.kraken.com"
    # Composite provider: per-asset-class routing
    MARKET_EQUITY_PROVIDER: str = "mock"
    MARKET_CRYPTO_PROVIDER: str = "kraken"
    MARKET_FOREX_PROVIDER: str = "twelvedata"

    # --- Market data: deterministic mock provider ----------------------------
    MOCK_MARKET_SEED: int = 42
    MOCK_MARKET_SYMBOLS: str = "AAPL,MSFT,NVDA,TSLA,AMZN,SPY"
    MOCK_MARKET_START_PRICE: float = 100.0
    MOCK_MARKET_VOLATILITY: float = 0.02
    MOCK_MARKET_IS_OPEN: bool = True
    # Deterministic scenario mode (empty = pseudo-random walk). See
    # app/market/providers/scenarios.py.
    MOCK_MARKET_SCENARIO: str = ""

    # --- Market data: CSV provider -------------------------------------------
    CSV_MARKET_DATA_PATH: str = ""
    CSV_MARKET_DATA_IS_OPEN: bool = True

    # --- Strategies ----------------------------------------------------------
    # All thresholds are engineering defaults, not investment advice.
    STRATEGY_AUTO_BOOTSTRAP: bool = True
    STRATEGY_DEFAULT_TIMEFRAME: str = "1h"
    STRATEGY_SIGNAL_TTL_MULTIPLIER: float = 2.0
    # Analysis staleness: refuse evaluation when the newest candle is older than
    # timeframe_seconds * multiplier (looser than execution freshness).
    STRATEGY_ANALYSIS_MAX_AGE_MULTIPLIER: float = 3.0

    STRATEGY_TREND_FAST_PERIOD: int = 20
    STRATEGY_TREND_SLOW_PERIOD: int = 50
    STRATEGY_TREND_ATR_PERIOD: int = 14
    STRATEGY_TREND_SLOPE_LOOKBACK: int = 10
    STRATEGY_TREND_MIN_MA_SPREAD_BPS: float = 10.0
    STRATEGY_TREND_MIN_CONFIDENCE: float = 0.5
    STRATEGY_TREND_ALLOW_HIGH_VOLATILITY: bool = False

    STRATEGY_MOMENTUM_RSI_PERIOD: int = 14
    STRATEGY_MOMENTUM_MACD_FAST_PERIOD: int = 12
    STRATEGY_MOMENTUM_MACD_SLOW_PERIOD: int = 26
    STRATEGY_MOMENTUM_MACD_SIGNAL_PERIOD: int = 9
    STRATEGY_MOMENTUM_VOLUME_PERIOD: int = 20
    STRATEGY_MOMENTUM_MIN_RELATIVE_VOLUME: float = 1.0
    STRATEGY_MOMENTUM_MIN_CONFIDENCE: float = 0.5
    STRATEGY_MOMENTUM_ALLOW_HIGH_VOLATILITY: bool = False

    STRATEGY_MEAN_REVERSION_BOLLINGER_PERIOD: int = 20
    STRATEGY_MEAN_REVERSION_BOLLINGER_STDDEV: float = 2.0
    STRATEGY_MEAN_REVERSION_PERCENT_B_LOW: float = 0.05
    STRATEGY_MEAN_REVERSION_PERCENT_B_HIGH: float = 0.95
    STRATEGY_MEAN_REVERSION_REQUIRE_CONFIRMATION: bool = True
    STRATEGY_MEAN_REVERSION_MIN_CONFIDENCE: float = 0.5
    STRATEGY_MEAN_REVERSION_ALLOW_TRENDING: bool = False

    STRATEGY_RSI_OVERSOLD: float = 30.0
    STRATEGY_RSI_OVERBOUGHT: float = 70.0

    # --- Market regime -------------------------------------------------------
    REGIME_FAST_PERIOD: int = 20
    REGIME_SLOW_PERIOD: int = 50
    REGIME_ATR_PERIOD: int = 14
    REGIME_SLOPE_LOOKBACK: int = 10
    REGIME_TREND_MIN_SPREAD_BPS: float = 10.0
    REGIME_HIGH_VOLATILITY_ATR_PERCENT: float = 3.0
    REGIME_LOW_VOLATILITY_ATR_PERCENT: float = 1.0

    # --- Risk engine ---------------------------------------------------------
    RISK_ENABLED: bool = True
    # Existing MAX_*/MINIMUM_* settings above are the canonical defaults; the
    # RiskSettings persisted row overrides them per user.
    RISK_MAX_RISK_PER_TRADE_PERCENT: float = 1.0
    RISK_REQUIRE_STRATEGY_SIGNAL: bool = False
    RISK_UNKNOWN_SECTOR_POLICY: str = "warn"  # reject|allow|warn
    RISK_DAILY_LOSS_INCLUDE_UNREALIZED: bool = True
    RISK_COMMISSION_BUFFER_BPS: float = 5.0
    RISK_WARNING_UTILIZATION_PERCENT: float = 80.0
    RISK_CRITICAL_UTILIZATION_PERCENT: float = 100.0
    RISK_DEFAULT_TRADING_STATE: KillSwitchState = "TRADING_ENABLED"

    # --- LLM / Agent ---------------------------------------------------------
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = ""
    LLM_API_KEY: str = ""
    LLM_TEMPERATURE: float = 0.0
    AGENT_ENABLED: bool = False

    # --- AI providers (Phase 9) ---------------------------------------------
    AI_ENABLED: bool = True
    # urlsafe base64 32-byte Fernet key; required to store/read API tokens.
    AI_CREDENTIAL_ENCRYPTION_KEY: str = ""
    AI_ALLOW_CUSTOM_BASE_URL: bool = True
    AI_ALLOW_PRIVATE_BASE_URL: bool = False
    AI_ALLOW_HTTP_BASE_URL: bool = False
    AI_HTTP_TIMEOUT_SECONDS: float = 30.0

    # --- TradingAnalysisAgent (Phase 9B) -------------------------------------
    AGENT_DEFAULT_MODE: str = "ANALYSIS_ONLY"
    AGENT_MAX_TOOL_ITERATIONS: int = 8
    AGENT_RUN_TIMEOUT_SECONDS: int = 60
    AGENT_MAX_CONCURRENT_RUNS_PER_USER: int = 2
    AGENT_MAX_RUNS_PER_MINUTE: int = 10
    AGENT_MAX_OUTPUT_TOKENS: int = 1500
    AGENT_TEMPERATURE: float = 0.0
    AGENT_MAX_PROMPT_CHARS: int = 2000

    # --- Risk settings (conservative examples, not financial advice) --------
    MAX_POSITION_PERCENTAGE: float = 5.0
    MAX_PORTFOLIO_EXPOSURE: float = 80.0
    MAX_OPEN_POSITIONS: int = 10
    MAX_DAILY_LOSS_PERCENTAGE: float = 2.0
    MAX_DRAWDOWN_PERCENTAGE: float = 15.0
    MAX_TRADES_PER_DAY: int = 20
    MINIMUM_CONFIDENCE: float = 0.6
    MINIMUM_RISK_REWARD_RATIO: float = 2.0
    MAX_SECTOR_EXPOSURE: float = 30.0
    MAX_ASSET_CLASS_EXPOSURE: float = 60.0
    REQUIRE_STOP_LOSS: bool = True

    # --- System --------------------------------------------------------------
    KILL_SWITCH_STATE: KillSwitchState = "TRADING_ENABLED"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("JWT_SECRET")
    @classmethod
    def _validate_jwt_secret(cls, value: str, info) -> str:
        environment = info.data.get("ENVIRONMENT")
        if environment == "production" and (not value or value == "change-me-in-production"):
            raise ValueError("JWT_SECRET must be set to a strong value in production")
        if environment == "production" and len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
        return value

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @model_validator(mode="after")
    def _validate_ranges(self) -> Settings:
        """Fail fast on nonsensical strategy/regime/risk configuration."""
        if self.STRATEGY_TREND_FAST_PERIOD >= self.STRATEGY_TREND_SLOW_PERIOD:
            raise ValueError("STRATEGY_TREND_FAST_PERIOD must be < STRATEGY_TREND_SLOW_PERIOD")
        if self.STRATEGY_MOMENTUM_MACD_FAST_PERIOD >= self.STRATEGY_MOMENTUM_MACD_SLOW_PERIOD:
            raise ValueError("MACD fast period must be < slow period")
        if self.REGIME_FAST_PERIOD >= self.REGIME_SLOW_PERIOD:
            raise ValueError("REGIME_FAST_PERIOD must be < REGIME_SLOW_PERIOD")
        if not 0 < self.STRATEGY_RSI_OVERSOLD < self.STRATEGY_RSI_OVERBOUGHT < 100:
            raise ValueError("RSI thresholds must satisfy 0 < oversold < overbought < 100")
        if (
            self.STRATEGY_MEAN_REVERSION_PERCENT_B_LOW
            >= self.STRATEGY_MEAN_REVERSION_PERCENT_B_HIGH
        ):
            raise ValueError("Mean-reversion percent-B low must be < high")
        if self.REGIME_HIGH_VOLATILITY_ATR_PERCENT <= self.REGIME_LOW_VOLATILITY_ATR_PERCENT:
            raise ValueError("High-volatility ATR%% must exceed low-volatility ATR%%")
        for name in (
            "MAX_POSITION_PERCENTAGE",
            "MAX_PORTFOLIO_EXPOSURE",
            "MAX_DAILY_LOSS_PERCENTAGE",
            "MAX_DRAWDOWN_PERCENTAGE",
            "MAX_SECTOR_EXPOSURE",
            "MAX_ASSET_CLASS_EXPOSURE",
            "RISK_MAX_RISK_PER_TRADE_PERCENT",
        ):
            value = getattr(self, name)
            if not 0 < value <= 100:
                raise ValueError(f"{name} must be in (0, 100]")
        for name in ("MAX_OPEN_POSITIONS", "MAX_TRADES_PER_DAY"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be > 0")
        if not 0 <= self.MINIMUM_CONFIDENCE <= 1:
            raise ValueError("MINIMUM_CONFIDENCE must be in [0, 1]")
        if self.MINIMUM_RISK_REWARD_RATIO <= 0:
            raise ValueError("MINIMUM_RISK_REWARD_RATIO must be > 0")
        if self.RISK_WARNING_UTILIZATION_PERCENT >= self.RISK_CRITICAL_UTILIZATION_PERCENT:
            raise ValueError("Risk warning utilization must be < critical utilization")
        if self.RISK_UNKNOWN_SECTOR_POLICY not in {"reject", "allow", "warn"}:
            raise ValueError("RISK_UNKNOWN_SECTOR_POLICY must be reject|allow|warn")
        return self

    @property
    def market_symbols(self) -> list[str]:
        """Active symbol universe (``MARKET_SYMBOLS`` else the mock list)."""
        source = self.MARKET_SYMBOLS or self.MOCK_MARKET_SYMBOLS
        seen: dict[str, None] = {}
        for raw in source.split(","):
            symbol = raw.strip().upper()
            if symbol:
                seen.setdefault(symbol, None)
        return list(seen)

    @property
    def worker_strategy_symbols(self) -> list[str]:
        """Symbols the strategy-evaluation worker should run; defaults to the universe."""
        source = self.WORKER_STRATEGY_SYMBOLS or self.MOCK_MARKET_SYMBOLS
        seen: dict[str, None] = {}
        for raw in source.split(","):
            symbol = raw.strip().upper()
            if symbol:
                seen.setdefault(symbol, None)
        return list(seen)

    @property
    def sync_database_url(self) -> str:
        """Synchronous SQLAlchemy URL used by Alembic."""
        url = self.DATABASE_URL
        url = url.replace("+asyncpg", "+psycopg")
        url = url.replace("+aiosqlite", "")
        return url

    def live_trading_allowed(self) -> tuple[bool, list[str]]:
        """Evaluate the multi-condition live trading interlock.

        Returns ``(allowed, missing_requirements)``. Live trading is refused when
        any requirement is missing, regardless of how the request originated.
        """
        missing: list[str] = []
        if self.TRADING_MODE != "live":
            missing.append("TRADING_MODE must be 'live'")
        if not self.LIVE_TRADING_ENABLED:
            missing.append("LIVE_TRADING_ENABLED must be true")
        if not self.BROKER_LIVE_CREDENTIALS_PRESENT:
            missing.append("BROKER_LIVE_CREDENTIALS_PRESENT must be true")
        if not self.MANUAL_LIVE_ACTIVATION:
            missing.append("MANUAL_LIVE_ACTIVATION must be true")
        return (len(missing) == 0, missing)


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
