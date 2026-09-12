# Aegis Trader

A production-oriented, AI-assisted automated trading platform for personal use.
**V1 runs in paper-trading mode only.** The LLM is architecturally forbidden from
touching broker execution: it may only create a `TradeProposal`, which must pass
through the deterministic Risk Engine before any order can exist.

> ⚠️ **Not financial advice.** All default risk values and balances in this
> repository are conservative *examples* to be tuned by the operator. Nothing
> here guarantees profit or suitability for any market.

---

## Architecture

```
Market Data
   │
   ▼
Strategy Engine          (deterministic, Phase 5)
   │
   ▼
Trading / Analysis Agent (LLM, Phase 9)  ── create_trade_proposal only
   │
   ▼
TradeProposal
   │
   ═══════════════ NO LLM BELOW THIS LINE ═══════════════
   │
   ▼
Risk Engine              (deterministic, Phase 6)
   │
   ▼
Order Manager            (idempotent, Phase 7)
   │
   ▼
Broker Adapter           (Phase 3)
   │
   ▼
Paper Trading Broker
```

The boundary is enforced, not merely prompted:
- The `app.agents` / `app.strategies` packages cannot import execution modules.
- `tests/test_architecture.py` fails if that boundary is ever crossed.
- Live execution is refused unless **all** interlock conditions are met:
  `TRADING_MODE=live`, `LIVE_TRADING_ENABLED=true`,
  `BROKER_LIVE_CREDENTIALS_PRESENT=true`, `MANUAL_LIVE_ACTIVATION=true`.

---

## Repository layout

```
trading-platform/
├── backend/            FastAPI + SQLAlchemy (async) + Alembic
│   ├── app/
│   │   ├── api/        REST routers (v1) + error handlers
│   │   ├── auth/       Auth service + dependencies
│   │   ├── agents/     AI agent layer (Phase 9)   ┐
│   │   ├── strategies/ Strategy engine (Phase 5)  │ no broker imports
│   │   ├── risk/       Risk engine (Phase 6)      ┘
│   │   ├── brokers/    Broker adapters (Phase 3)
│   │   ├── orders/     Order manager (Phase 7)
│   │   ├── market/     Market data (Phase 2)
│   │   ├── portfolio/  Portfolio service (Phase 4)
│   │   ├── backtesting/Backtester (Phase 8)
│   │   ├── models/     Domain models (all core entities)
│   │   ├── schemas/    Pydantic request/response models
│   │   ├── repositories/ Async data access
│   │   ├── services/   Business logic
│   │   ├── websocket/  Realtime channels (Phase 4)
│   │   ├── workers/    Background tasks
│   │   └── core/       Config, logging, security, errors
│   ├── migrations/     Alembic
│   ├── scripts/        entrypoint + seed
│   └── tests/
├── mobile/             Flutter client (Riverpod, GoRouter, Dio)
├── web/                Browser terminal (Nuxt 4, Vue 3, TanStack Query)
├── docker-compose.yml  PostgreSQL + Redis + backend
└── .gitignore
```

---

## Quick start

### 1. Backend with Docker (recommended)

```bash
cp backend/.env.example .env          # edit JWT_SECRET etc.
docker compose up --build
```

The entrypoint applies migrations automatically. API: http://localhost:8000/docs

Create the owner account and default paper portfolio:

```bash
docker compose exec backend python -m scripts.seed \
  --email owner@example.com --password 'change-me-strong-password'
```

### 2. Backend without Docker

Requires Python 3.12+, PostgreSQL and Redis.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                  # edit values
alembic upgrade head
python -m scripts.seed --email owner@example.com --password 'change-me-strong-password'
uvicorn app.main:app --reload
```

### 3. Mobile app

Requires the Flutter SDK (stable).

```bash
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000 \
            --dart-define=WS_BASE_URL=ws://10.0.2.2:8000
```

Use `http://localhost:8000` for the iOS simulator or desktop, and your machine's
LAN IP for a physical device.

---

## Verifying

```bash
# Backend
cd backend && source .venv/bin/activate
pytest            # 27 tests, isolated SQLite (no Postgres/Redis needed)
ruff check app tests

# Mobile
cd mobile
flutter analyze   # No issues
flutter test      # 7 tests
```

---

## Key endpoints (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Aggregate component health |
| GET | `/api/v1/health/live` | Liveness probe |
| GET | `/api/v1/health/ready` | Readiness probe (DB required) |
| GET | `/api/v1/system/status` | Trading mode + live-trading interlock |
| GET | `/api/v1/auth/registration-open` | Whether bootstrap registration is allowed |
| POST | `/api/v1/auth/register` | Create the bootstrap owner account |
| POST | `/api/v1/auth/login` | Login (returns access + refresh tokens) |
| POST | `/api/v1/auth/refresh` | Rotate refresh token |
| POST | `/api/v1/auth/logout` | Revoke a session |
| GET | `/api/v1/auth/me` | Current user |
| GET | `/api/v1/auth/sessions` | Active device sessions |

Full OpenAPI docs at `/docs`.

---

## API documentation

The full OpenAPI 3.1 contract is available three ways:

- `GET /api/docs` — interactive ReDoc page
- `GET /api/docs/openapi.yaml` — raw YAML spec
- [`api/docs/openapi.yaml`](api/docs/openapi.yaml) — committed copy in this repo

Regenerate the committed spec after changing routes:

```bash
cd backend && source .venv/bin/activate && python -m scripts.export_openapi
```

## Deployment

The backend is **live on the Lenovo server at
https://traderbackend.awesometech.com.ng** (paper mode, Docker + shared Cloudflare
Tunnel). See [`deploy/README.md`](deploy/README.md) for the full runbook and
current status.

The mobile app defaults to this backend; build it with the production defines:

```bash
cd mobile
flutter build apk --release --dart-define-from-file=dart_defines/prod.json
```

## Browser terminal (`web/`)

Live at **https://trader.awesometech.com.ng**.

A purpose-built professional trading terminal (not a generic admin dashboard).
It is a secure presentation and control layer: it never talks to a broker or
exchange and never makes trading, risk or strategy decisions.

- **Stack**: Nuxt 4 · Vue 3 (`<script setup lang="ts">`) · strict TypeScript ·
  Tailwind v4 (via Nuxt UI) · Pinia · TanStack Query · VueUse · Zod · ECharts ·
  TradingView Lightweight Charts · Vitest · Playwright
- **Server state** lives in TanStack Query; **client state** in Pinia.
- One shared WebSocket feeds targeted query-cache invalidation and the
  notification centre.
- Dark-first, dense, numerically legible; a persistent **PAPER TRADING**
  indicator is always visible.

```bash
cd web
npm install
cp .env.example .env
npm run dev        # http://localhost:3000
npm run typecheck && npm run lint && npm test && npm run build
```

Backend endpoints the web app expects but that are not implemented yet are
tracked in [`web/docs/missing-endpoints.md`](web/docs/missing-endpoints.md).

## Development phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Foundation: FastAPI, config, Postgres/Redis, models, Alembic, health, auth, Docker, Flutter skeleton | ✅ Done |
| 2 | Market data provider, candles, quotes, indicators | ✅ Done |
| 3 | Paper broker (fills, slippage, fees, P&L) | ✅ Done |
| 4 | Portfolio service, snapshots, REST + WebSocket, notifications | ✅ Done |
| 5 | Trend / momentum / mean-reversion strategies | ✅ Done |
| 6 | Deterministic Risk Engine + kill switch | ✅ Done |
| 7 | TradeProposal → Risk → OrderManager pipeline | ⏭ Next |
| 8 | Backtesting engine + Flutter UI | |
| 9 | TradingAnalysisAgent (read tools + create_trade_proposal only) | |
| 10 | Flutter completion, offline cache, notifications | |
| 11 | Extended multi-agent intelligence | |

### Phase 7 — next task

Wire the execution pipeline: `TradeProposal` → `RiskRequest` →
`RiskEngine.evaluate()` → `RiskEvaluation` (APPROVED) → `OrderManager` →
`MarketDataService.get_fresh_quote()` → final risk revalidation →
`BrokerAdapter.submit_order()`, with idempotency and the existing audit/event
infrastructure. Strategies and the Risk Engine never submit orders themselves.

---

## Security notes

- Secrets live server-side only; the mobile app never sees broker or LLM keys.
- Passwords are hashed with bcrypt; tokens are short-lived JWTs with rotation.
- All logs pass through a redaction processor that strips credential-like keys.
- Every configuration value is environment-driven; `.env` is git-ignored.

## License

Proprietary — personal use.
