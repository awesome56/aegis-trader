# Missing backend APIs (as consumed by the web terminal)

The web frontend is fully typed against the agreed API contract. The endpoints
below are **not yet implemented** on the backend; the corresponding services will
return `404`/`network_error` until they are added. During development set
`NUXT_PUBLIC_USE_MOCK_API=true` to use isolated fixtures. Production never falls
back to mocks.

## Live (implemented)

- `GET /api/v1/health`, `/health/live`, `/health/ready`
- `POST /api/v1/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`
- `GET /api/v1/auth/me`, `/auth/sessions`, `/auth/registration-open`
- `GET /api/v1/system/status`

## Required by Phase 2+ (not implemented)

| Method | Path | Used by |
|--------|------|---------|
| GET | `/api/v1/dashboard` | Dashboard |
| GET | `/api/v1/portfolio` | Portfolio |
| GET | `/api/v1/portfolio/history` | Equity curve |
| GET | `/api/v1/portfolio/allocation` | Allocation panels |
| GET | `/api/v1/positions` | Positions |
| GET | `/api/v1/positions/{id}` | Position workspace |
| GET | `/api/v1/markets` | Watchlist / market overview |
| GET | `/api/v1/markets/search` | Symbol search |
| GET | `/api/v1/markets/{symbol}` | Asset detail |
| GET | `/api/v1/markets/{symbol}/candles` | Candlestick charts |
| GET | `/api/v1/markets/{symbol}/quote` | Quotes |
| GET | `/api/v1/trades` | Trades |
| GET | `/api/v1/trades/{id}` | Trade audit |
| GET | `/api/v1/orders` | Orders |
| GET | `/api/v1/orders/{id}` | Order detail |
| GET | `/api/v1/proposals` | Proposals |
| GET | `/api/v1/proposals/{id}` | Proposal detail |
| GET | `/api/v1/proposals/{id}/pipeline` | Decision pipeline |
| GET | `/api/v1/agent/status` | Agent overview |
| GET | `/api/v1/agent/decisions` | Decision records |
| GET | `/api/v1/strategies` | Strategies |
| GET | `/api/v1/strategies/{id}` | Strategy detail |
| POST | `/api/v1/strategies/{id}/enable\|disable` | Strategy control |
| GET | `/api/v1/risk` | Risk centre |
| GET | `/api/v1/risk/limits` | Risk limits |
| GET | `/api/v1/risk/settings` | Risk settings |
| PUT | `/api/v1/risk/settings` | Risk settings (write) |
| GET | `/api/v1/risk/events` | Risk events |
| GET | `/api/v1/backtests` | Backtests |
| POST | `/api/v1/backtests` | Run backtest |
| GET | `/api/v1/backtests/{id}` | Backtest |
| GET | `/api/v1/backtests/{id}/result` | Backtest result |
| GET | `/api/v1/activity` | Audit timeline |
| POST | `/api/v1/system/pause` | Trading controls |
| POST | `/api/v1/system/resume` | Trading controls |
| POST | `/api/v1/system/emergency-stop` | Trading controls |

## Backend WebSocket channel (not implemented)

`GET /ws?token=…` — typed envelopes `{ event, timestamp, data }`. Event names are
enumerated in `app/types/websocket.ts` (`order.filled`, `risk.warning`,
`agent.completed`, `system.status_changed`, …).

## Other backend requirements surfaced during Phase 1

- **HttpOnly cookie sessions**: the frontend currently persists the refresh
  token in a SameSite=Strict cookie set by JavaScript. A backend-issued
  HttpOnly cookie would remove JS access to tokens entirely.
