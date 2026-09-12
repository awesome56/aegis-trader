"""Configuration and live-trading interlock unit tests."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_defaults_are_paper_and_safe() -> None:
    settings = Settings(_env_file=None)
    assert settings.TRADING_MODE == "paper"
    assert settings.LIVE_TRADING_ENABLED is False
    assert settings.live_trading_allowed() == (
        False,
        [
            "TRADING_MODE must be 'live'",
            "LIVE_TRADING_ENABLED must be true",
            "BROKER_LIVE_CREDENTIALS_PRESENT must be true",
            "MANUAL_LIVE_ACTIVATION must be true",
        ],
    )


def test_live_trading_requires_all_conditions() -> None:
    settings = Settings(
        _env_file=None,
        TRADING_MODE="live",
        LIVE_TRADING_ENABLED=True,
        BROKER_LIVE_CREDENTIALS_PRESENT=True,
        MANUAL_LIVE_ACTIVATION=True,
    )
    assert settings.live_trading_allowed() == (True, [])


def test_partial_live_configuration_is_refused() -> None:
    settings = Settings(
        _env_file=None,
        TRADING_MODE="live",
        LIVE_TRADING_ENABLED=True,
        BROKER_LIVE_CREDENTIALS_PRESENT=False,
        MANUAL_LIVE_ACTIVATION=True,
    )
    allowed, missing = settings.live_trading_allowed()
    assert allowed is False
    assert missing == ["BROKER_LIVE_CREDENTIALS_PRESENT must be true"]


def test_sync_database_url_swaps_async_drivers() -> None:
    pg = Settings(_env_file=None, DATABASE_URL="postgresql+asyncpg://u:p@h:5432/db")
    assert pg.sync_database_url == "postgresql+psycopg://u:p@h:5432/db"

    sqlite = Settings(_env_file=None, DATABASE_URL="sqlite+aiosqlite:///./x.db")
    assert sqlite.sync_database_url == "sqlite:///./x.db"


def test_production_requires_strong_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENVIRONMENT="production", JWT_SECRET="short")


def test_cors_origins_parses_json_string() -> None:
    settings = Settings(_env_file=None, CORS_ORIGINS='["https://a.example", "https://b.example"]')
    assert settings.CORS_ORIGINS == ["https://a.example", "https://b.example"]
