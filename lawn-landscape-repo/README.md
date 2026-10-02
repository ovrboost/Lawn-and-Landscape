# Lawn & Landscape — Phase 1

Docker-hosted web app, installed on an Android phone as a PWA. Phase 1 covers:
login, customers and properties (manual entry and CSV import), and a Settings screen.
Maps, routes, quotes, mowers, check-in, and billing come in later phases (see the build plan).

## What's in the box

- `backend/` FastAPI + SQLAlchemy + Postgres. One account, single-password login, session cookie.
- `frontend/` React PWA (installable, opens offline from cache, never caches API data).
- `docker-compose.yml` Postgres and the app. The app listens on `127.0.0.1:8000` only.

## First run (home server)

```bash
cp .env.example .env
# edit .env: set POSTGRES_PASSWORD, APP_PASSWORD, and SECRET_KEY (openssl rand -hex 32)
docker compose up -d --build
curl http://127.0.0.1:8000/api/health     # {"ok":true}
```

## Reach it from your phone over HTTPS (Tailscale)

GPS and "Install app" need HTTPS. Tailscale gives you a real certificate with no port forwarding.

1. Install Tailscale on the server and on the phone; sign in to the same account.
2. In the Tailscale admin console → DNS, turn on **MagicDNS** and **HTTPS Certificates**.
3. On the server: `sudo tailscale serve --bg 8000`
4. It prints a URL like `https://your-server.your-tailnet.ts.net`. Open it in Chrome on the phone.
5. Sign in, then Chrome menu → **Install app** (or **Add to Home screen**).

Phase 1 gate: the app installs on the phone and opens over HTTPS.

## Using it

- **Customers → Add**: name, email, phone, then one or more properties (address, monthly flat or per-visit price, lot size).
- **Import**: download the template, fill it in, upload. You see a preview first. A row matches an existing
  customer by email (or by name when there is no email) and a property by normalized address, and is skipped
  only when both match. A second address for the same email becomes a new property.
- **Settings**: base address, quote pricing, sales tax (0 = off), late fee (flat or percent, grace days),
  Gmail address and app password (stored encrypted, not used until billing is built), change app password.

## Backups

`./scripts/backup.sh` writes a compressed Postgres dump to `backups/` and keeps the newest 30.
Schedule it with cron and copy the folder to a second location. Restore:
`gunzip -c backups/FILE.sql.gz | docker compose exec -T db psql -U lawn lawn`

## Notes for later phases

- Addresses are saved but not geocoded yet; `lat`/`lng` are empty until phase 2.
- Tables are created on startup. Before the schema changes in phase 2, add Alembic migrations.
- `SECRET_KEY` must stay the same. Changing it logs you out and makes the saved Gmail password unreadable
  (you would just re-enter it in Settings).
- Deleting a customer is permanent in phase 1; once visits exist (phase 4) deletion will be blocked in favor of "inactive".

## Develop / test

```bash
cd backend && pip install -r requirements-dev.txt && pytest
cd frontend && npm install && npm run dev      # proxies /api to localhost:8000
```
