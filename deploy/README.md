# Deploying to the Lenovo server (`lenovo` / `rider.awesometech.com.ng`)

Server: Ubuntu 24.04, 4 vCPU, 7.6 GB RAM, `192.168.1.10` behind NAT, Tailscale
`100.119.144.46`. Docker is **not** pre-installed; the steps below install it.

## 0. One-time: install Docker on the server

```bash
ssh lenovo 'curl -fsSL https://get.docker.com | sudo sh'
ssh lenovo 'sudo usermod -aG docker $USER'   # re-login for group to apply
```

## 1. Clone the private repository

```bash
ssh lenovo
git clone https://github.com/awesome56/aegis-trader.git ~/aegis-trader
cd ~/aegis-trader
cp .env.prod.example .env.prod
# edit .env.prod: set POSTGRES_PASSWORD and a 64-char JWT_SECRET
```

Generate a JWT secret locally and paste it:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

## 2. Start the stack

```bash
./deploy/deploy.sh --seed owner@example.com 'a-strong-password'
```

This builds the image, starts PostgreSQL, Redis and the backend, applies Alembic
migrations via the container entrypoint, and creates your owner account. The
backend binds only to `127.0.0.1:8000`.

The API is then reachable **on the server** at
`http://127.0.0.1:8000/api/docs/openapi.yaml`.

## 3. Public exposure — pick ONE

### Option A (recommended): Cloudflare Tunnel

No router changes and TLS is handled by Cloudflare.

This server already runs the shared `examco-tunnel` (`77474f43-…`, service
`cloudflared`) that fronts `agent`, `files`, `qa`, `power`, etc. `rider` was
added to that same tunnel, so no new tunnel is required.

```bash
# one-off (already done):
sudo python3 deploy/cloudflare/add_ingress.py \
    rider.awesometech.com.ng http://localhost:8899
cloudflared tunnel route dns examco-tunnel rider.awesometech.com.ng
sudo systemctl restart cloudflared
```

Live check:

```bash
curl https://rider.awesometech.com.ng/api/v1/health
```

### Option B: router port-forwarding + host nginx + Let's Encrypt

1. Forward WAN ports 80 and 443 to `192.168.1.10` on the router.
2. Point a Cloudflare **DNS-only (grey cloud)** A record for
   `rider.awesometech.com.ng` at the public IP.
3. Install the nginx site and enable TLS:

```bash
sudo cp deploy/nginx/rider.awesometech.com.ng.conf \
        /etc/nginx/sites-available/rider.awesometech.com.ng
sudo ln -s /etc/nginx/sites-available/rider.awesometech.com.ng \
           /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d rider.awesometech.com.ng
```

## 4. Operations

```bash
cd ~/aegis-trader
git pull
./deploy/deploy.sh                       # rebuild + restart, migrations run automatically
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f backend
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

Rotate the owner password (the seed script creates a temporary one):

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T backend \
  python -m scripts.set_password --email owner@awesometech.com.ng --password 'new-strong-password'
```

## 5. Current live state

| Item | Value |
|------|-------|
| Public API | https://rider.awesometech.com.ng |
| OpenAPI YAML | https://rider.awesometech.com.ng/api/docs/openapi.yaml |
| ReDoc | https://rider.awesometech.com.ng/api/docs |
| Health | https://rider.awesometech.com.ng/api/v1/health |
| Backend bind | `127.0.0.1:8899` (Docker → container :8000) |
| Tunnel | shared `examco-tunnel` (`cloudflared.service`) |
| Trading mode | paper (live interlock locked) |

## Notes / cautions

- The server already runs other services (nginx, Postgres on 127.0.0.1:5432,
  apps on 8228/8290). This stack deliberately does **not** publish the DB/Redis
  ports and binds the backend to `127.0.0.1:8000` to avoid collisions.
- Live trading stays disabled: paper mode only, enforced by the backend
  interlock.
- Secrets live only in `.env.prod` on the server (git-ignored).
