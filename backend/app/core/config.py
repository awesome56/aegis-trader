"""Application configuration loaded from environment variables.

All financial and risk values below are *conservative examples* intended to be
overridden per deployment. They are not financial advice.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
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
    BROKER_PAPER_PARTIAL_FILLS: bool = True

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

    # --- Market data: deterministic mock provider ----------------------------
    MOCK_MARKET_SEED: int = 42
    MOCK_MARKET_SYMBOLS: str = "AAPL,MSFT,NVDA,TSLA,AMZN,SPY"
    MOCK_MARKET_START_PRICE: float = 100.0
    MOCK_MARKET_VOLATILITY: float = 0.02
    MOCK_MARKET_IS_OPEN: bool = True

    # --- Market data: CSV provider -------------------------------------------
    CSV_MARKET_DATA_PATH: str = ""
    CSV_MARKET_DATA_IS_OPEN: bool = True

    # --- LLM / Agent ---------------------------------------------------------
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = ""
    LLM_API_KEY: str = ""
    LLM_TEMPERATURE: float = 0.0
    AGENT_ENABLED: bool = False

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

    @property
    def market_symbols(self) -> list[str]:
        """Configured mock/generic symbol universe, normalised and de-duplicated."""
        seen: dict[str, None] = {}
        for raw in self.MOCK_MARKET_SYMBOLS.split(","):
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
