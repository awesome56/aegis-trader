# Aegis Trader — Backend

AI-assisted, risk-gated automated trading platform. **V1 is paper-trading only.**
The LLM may only create a `TradeProposal`; deterministic components below the
"risk line" own all order execution.

See the repository root `README.md` for full setup and architecture.

## Quick start (local)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # edit values (JWT_SECRET, DATABASE_URL, ...)
# Requires PostgreSQL + Redis, or use the root docker-compose:
#   docker compose up db redis
alembic upgrade head
python -m scripts.seed --email owner@example.com --password 'a-strong-password'
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs
Health: http://localhost:8000/api/v1/health

## Tests

```bash
pytest
```
The test suite uses an isolated SQLite database and requires no external
services. Redis is expected to be reported `unhealthy` in tests.

## Architecture boundary

```
Market Data → Strategy Engine → Trading/Agent → TradeProposal
                                                        │
                       ─────────── NO LLM BELOW THIS LINE ───────────
                                                        ▼
                                    RiskManager → OrderManager → BrokerAdapter → PaperBroker
```

## Market data (Phase 2)

Provider-independent market-data subsystem. Trading code depends only on
`MarketDataProvider`; provider SDKs stay inside `app/market/providers/`.

```
MarketDataService
  └─ MarketDataProvider (mock | csv | future: alpaca/polygon/…)
       └─ validation → repositories (PostgreSQL) → Redis cache
```

- **Flow**: cache → database → provider → validate → persist → cache → return.
- **Fail-closed freshness**: `get_fresh_quote()` / `get_fresh_candles()` raise
  `StaleMarketDataError` using the **market timestamp** (never the receive time).
  The Order Manager (Phase 7) will call these before execution.
- **Indicators** (`app/market/indicators/`): pure, framework-free SMA, EMA, RSI
  (Wilder), MACD, ATR (Wilder), Bollinger Bands and volume analysis. Strategies
  interpret these later; indicators never emit BUY/SELL.

### Providers

| Provider | Selection | Notes |
|----------|-----------|-------|
| `mock` | `MARKET_DATA_PROVIDER=mock` | Deterministic; same seed + inputs ⇒ identical data. No network. |
| `csv` | `MARKET_DATA_PROVIDER=csv` + `CSV_MARKET_DATA_PATH` | Directory of `{SYMBOL}_{timeframe}.csv`, or one file with `symbol`+`timeframe` columns. |

CSV format — required columns
`timestamp,open,high,low,close,volume`; optional `symbol,timeframe,trade_count,vwap`.
Timestamps are ISO 8601 (naive values are treated as UTC and logged). Malformed
rows, duplicate timestamps and impossible candles are rejected, never ignored.
Sample fixtures live in `tests/fixtures/`.

### Adding a provider

1. Implement `MarketDataProvider` in `app/market/providers/<name>.py`.
2. Translate provider errors into `app.market.exceptions`.
3. Register it in `providers/factory.py`.
4. Add tests. No changes are needed anywhere else.

### Endpoints (authenticated)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/markets/status` | Market session status |
| `GET /api/v1/markets/search?q=` | Asset search |
| `GET /api/v1/markets/{symbol}/quote` | Latest quote + freshness (`age_seconds`, `is_stale`) |
| `GET /api/v1/markets/{symbol}/candles?timeframe=&start=&end=&limit=` | Historical candles |
| `GET /api/v1/markets/{symbol}/indicators?timeframe=&limit=` | SMA/EMA/RSI/MACD/ATR/Bollinger/volume |

Provider health appears in `GET /api/v1/health` (`market_data` component) and
`GET /api/v1/system/status` (`market_data_status`).

### Key configuration

`MARKET_DATA_PROVIDER`, `MARKET_QUOTE_CACHE_TTL_SECONDS`,
`MARKET_CANDLE_CACHE_TTL_SECONDS`, `MARKET_STATUS_CACHE_TTL_SECONDS`,
`MAX_QUOTE_AGE_SECONDS`, `MAX_INTRADAY_CANDLE_AGE_SECONDS`,
`MAX_DAILY_CANDLE_AGE_SECONDS`, `MARKET_MAX_CANDLE_LIMIT`,
`MOCK_MARKET_SEED`, `MOCK_MARKET_SYMBOLS`, `CSV_MARKET_DATA_PATH`.
See `.env.example` for the full list and defaults.

