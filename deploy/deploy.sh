#!/usr/bin/env bash
# Run this ON the Lenovo server from the repository root.
#
#   ./deploy/deploy.sh                 # build + start stack
#   ./deploy/deploy.sh --with-tunnel   # also start the Cloudflare Tunnel
#   ./deploy/deploy.sh --seed you@example.com 'strong-password'
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

COMPOSE=(docker compose --env-file .env.prod -f docker-compose.prod.yml)
WITH_TUNNEL=0
SEED_EMAIL=""
SEED_PASSWORD=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-tunnel) WITH_TUNNEL=1; shift ;;
    --seed) SEED_EMAIL="$2"; SEED_PASSWORD="$3"; shift 3 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ ! -f .env.prod ]]; then
  echo "ERROR: .env.prod not found. Copy .env.prod.example and fill it in." >&2
  exit 1
fi

if grep -q "change-me" .env.prod; then
  echo "ERROR: .env.prod still contains placeholder secrets (change-me)." >&2
  exit 1
fi

echo "==> building images"
"${COMPOSE[@]}" build

echo "==> starting stack"
"${COMPOSE[@]}" up -d

if [[ "$WITH_TUNNEL" == "1" ]]; then
  if ! grep -q '^CLOUDFLARE_TUNNEL_TOKEN=.\+' .env.prod; then
    echo "ERROR: CLOUDFLARE_TUNNEL_TOKEN is empty in .env.prod." >&2
    exit 1
  fi
  echo "==> starting Cloudflare Tunnel"
  "${COMPOSE[@]}" --profile tunnel up -d
fi

echo "==> waiting for backend health"
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/api/v1/health/live >/dev/null 2>&1; then
    echo "backend is live on http://127.0.0.1:8000"
    break
  fi
  sleep 2
done

if [[ -n "$SEED_EMAIL" ]]; then
  echo "==> seeding owner account $SEED_EMAIL"
  "${COMPOSE[@]}" exec -T backend python -m scripts.seed \
    --email "$SEED_EMAIL" --password "$SEED_PASSWORD"
fi

echo "==> status"
"${COMPOSE[@]}" ps
