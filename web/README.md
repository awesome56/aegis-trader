# Aegis Trader — Web Terminal

Browser-based monitoring, analytics, configuration and control interface for the
AI-assisted automated trading platform.

**The browser never talks to a broker or exchange and never makes trading, risk
or strategy decisions. The backend is authoritative.** The frontend is a secure
presentation and control layer.

## Architecture

```
Backend REST API                      Backend WebSocket
        │                                     │
        ▼                                     ▼
   API service layer                   WebSocket service
        │                                     │
        ▼                              Event router
   TanStack Query  ◀───────────────  cache invalidation + Pinia
        │
        ▼
   Vue components
```

- **Server state** → TanStack Query (`useDashboard`, `usePortfolio`, …)
- **Client state** → Pinia (auth session, UI preferences, notifications, socket status)
- Components never build URLs; all access goes through `app/services/api/*`

## Stack

Nuxt 4 · Vue 3 (`<script setup lang="ts">`) · strict TypeScript · Tailwind CSS v4
(via Nuxt UI) · Nuxt UI · Pinia · TanStack Query for Vue · VueUse · Zod ·
VeeValidate · Apache ECharts · TradingView Lightweight Charts · date-fns ·
Lucide (Iconify) · Vitest + Vue Test Utils · Playwright

> Tailwind v4 is CSS-first, so design tokens live in
> `app/assets/css/main.css` rather than a `tailwind.config.ts`.

## Setup

```bash
npm install
cp .env.example .env
npm run dev            # http://localhost:3000
```

### Environment

| Variable | Purpose |
|----------|---------|
| `NUXT_PUBLIC_API_BASE_URL` | Backend REST base URL (no `/api/v1`) |
| `NUXT_PUBLIC_WS_BASE_URL` | Backend WebSocket base URL |
| `NUXT_PUBLIC_USE_MOCK_API` | Serve isolated development mocks (never in production) |

```bash
NUXT_PUBLIC_API_BASE_URL=https://traderbackend.awesometech.com.ng
NUXT_PUBLIC_WS_BASE_URL=wss://traderbackend.awesometech.com.ng
NUXT_PUBLIC_USE_MOCK_API=true
```

## Commands

```bash
npm run dev            # development server
npm run typecheck      # nuxt typecheck (vue-tsc)
npm run lint           # eslint (Nuxt flat config)
npm run lint:fix
npm run format         # prettier
npm test               # vitest run (unit + component)
npm run test:coverage
npm run test:e2e       # playwright (requires `npx playwright install`)
npm run build          # production build
npm run preview
```

## Routes

| Route | Purpose | Delivered |
|-------|---------|-----------|
| `/login` | Authentication | Phase 1 |
| `/dashboard` | Command centre | Phase 2 |
| `/portfolio` | Allocation & performance | Phase 3 |
| `/positions`, `/positions/[id]` | Positions & workspace | Phase 3 |
| `/markets`, `/markets/[symbol]` | Watchlist & asset detail | Phase 4 |
| `/agent`, `/agent/proposals`, `/agent/proposals/[id]` | Agent & decision pipeline | Phase 5 |
| `/risk` | Risk control centre | Phase 6 |
| `/trades`, `/trades/[id]` | Trades & audit | Phase 7 |
| `/orders`, `/orders/[id]` | Order lifecycle | Phase 7 |
| `/strategies`, `/strategies/[id]` | Strategy engine | Phase 8 |
| `/backtests`, `/backtests/[id]` | Backtesting | Phase 9 |
| `/activity` | Audit timeline | Phase 10 |
| `/settings` | Appearance, account, system | Phase 10 |

## Authentication

- JWT access token held **in memory only** (`app/services/api/token.ts`).
- Refresh token persisted in a `SameSite=Strict` cookie and rotated by the API
  client on `401` (single-flight refresh).
- Global route middleware (`app/middleware/auth.ts`) guards all routes; `/login`
  opts out with `definePageMeta({ public: true })`.
- No broker/LLM/market-data credentials ever reach the browser.

> True HttpOnly cookie sessions require backend support and are noted as a
> backend requirement in `docs/missing-endpoints.md`.

## Realtime

A single shared socket (`app/services/websocket/client.ts`) is the **only**
WebSocket connection. It provides connection state, typed discriminated-union
events, automatic reconnect with exponential backoff + jitter, and duplicate
suppression. `useRealtime()` routes events into targeted TanStack Query
invalidation and the notification centre. Components never open sockets.

## Testing

- `tests/unit/**` — Vitest: formatters, websocket parsing, mocks, auth store,
  and dependency-light UI components.
- `tests/e2e/**` — Playwright smoke tests for routing/auth.

## Missing backend APIs

See [`docs/missing-endpoints.md`](docs/missing-endpoints.md). Services are fully
typed against the agreed contract; only `auth`, `system` and `health` are live
today. Production never silently falls back to mocks.
