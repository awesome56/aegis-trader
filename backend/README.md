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
