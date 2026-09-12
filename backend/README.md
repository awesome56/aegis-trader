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

## Paper broker (Phase 3)

A provider-neutral `BrokerAdapter` (`app/brokers/base.py`) with a deterministic
`PaperBrokerAdapter` (`app/brokers/paper.py`). The broker owns broker-side state
(cash, buying power, orders, fills, positions, realized P&L); `PortfolioService`
sits above it and never executes. Boundary tests enforce that `app.market` never
imports brokers and brokers never import portfolio/risk/strategy/agents.

Execution pricing always uses `MarketDataService.get_fresh_quote()` and **fails
closed** on stale data (no order is even created). Terminal state transitions are
validated in `app/brokers/state.py`.

| Order type | Behaviour |
|------------|-----------|
| MARKET | Fills immediately: BUY at the **ask**, SELL at the **bid**, plus slippage. |
| LIMIT | BUY eligible when ask ≤ limit; SELL when bid ≥ limit; otherwise rests open. |
| STOP | Triggers on `last` crossing the stop, then executes like MARKET. |
| STOP_LIMIT | Triggers on `last`, then behaves as LIMIT (not a guaranteed fill). |

`process_open_orders()` re-evaluates resting orders against fresh quotes.

## Portfolio, realtime & notifications (Phase 4)

`PortfolioService` aggregates the broker account into valuation, positions,
allocation, exposure, snapshots, history and drawdown. One `WebSocket` endpoint at
`/ws` (authenticated with a short-lived access token query parameter) delivers
typed envelopes `{event, event_id, timestamp, version, data}`. Notifications are
persisted and mirrored over the socket as `notification.created`.

## Accounting decisions (authoritative, `app/brokers/accounting.py`)

- **Commission**: flat fee per execution (`BROKER_PAPER_COMMISSION`), folded into
  the position cost basis on buys and deducted from proceeds on sells.
- **Slippage**: `BROKER_PAPER_SLIPPAGE_BPS`; BUY pays up, SELL receives less.
- **Spread**: `BROKER_PAPER_SPREAD_BPS` is a **half-spread**, applied only when a
  quote has no valid bid/ask (the mock/real providers supply their own).
- **Cost basis / average entry**: weighted average; buy commission capitalised.
- **Realized P&L**: `(exit - average_entry) * qty - sell_commission`.
- **Unrealized P&L mark**: conservative liquidation value — `bid` when available,
  else `last`.
- **Buying power**: `cash - reserved open BUY notional`.
- **Idempotency**: unique per `(broker_account, idempotency_key)`; survives
  restart (database constraint).

## Endpoints (Phase 3/4)

`GET /api/v1/dashboard` · `GET /api/v1/portfolio` ·
`GET /api/v1/portfolio/history?range=` · `GET /api/v1/portfolio/allocation` ·
`GET /api/v1/positions` · `GET /api/v1/positions/{id}` ·
`GET /api/v1/broker/{account,positions,positions/{symbol},quote/{symbol},clock,orders,orders/{id}}` ·
`POST /api/v1/broker/orders` (paper manual testing) ·
`DELETE /api/v1/broker/orders/{id}` · `POST /api/v1/broker/orders/process` ·
`GET /api/v1/notifications{,/unread-count}` ·
`POST /api/v1/notifications/{id}/read` · `POST /api/v1/notifications/read-all` ·
`WS /ws?token=`.

## Realtime events emitted

`order.created`, `order.submitted`, `order.partially_filled`, `order.filled`,
`order.cancelled`, `order.rejected`, `execution.created`, `position.created`,
`position.updated`, `position.closed`, `broker.account_updated`,
`notification.created`. Events are published **after a successful commit**
(best-effort, in-process). Agent/risk/strategy events are intentionally absent.
