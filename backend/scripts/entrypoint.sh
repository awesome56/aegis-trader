#!/usr/bin/env bash
set -euo pipefail

# Wait for PostgreSQL to accept connections, apply migrations, then exec CMD.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[entrypoint] applying database migrations..."
  alembic upgrade head
fi

echo "[entrypoint] starting: $*"
exec "$@"
