# 12 — Docker, Deployment and Operations

## 1. Target

One Linux VPS initially, Docker Compose, persistent volumes, reverse proxy, HTTPS, automated migrations/backups. Architecture can scale workers later without redesign.

## 2. Services

Suggested compose services:

```text
reverse-proxy
web
api
worker
scheduler
postgres
redis
(optional) prometheus
(optional) grafana
```

No database exposed publicly.

## 3. Environment

Provide:
- `.env.example` committed;
- `.env` ignored;
- Docker secrets or mounted secret files supported later.

Groups:
- app/auth;
- DB/Redis;
- TSETMC credentials/config;
- SEDRA credentials/config;
- data cadences/rate limits;
- feature/strategy defaults;
- paper/live-trading gates;
- optional NLP provider;
- observability.

## 4. Startup

Document:

```bash
git clone ...
cp .env.example .env
# edit credentials/domain
docker compose up -d --build
docker compose exec api alembic upgrade head
# bootstrap admin and initial sync through documented command
```

Prefer an entrypoint that checks migrations safely, but avoid multiple replicas racing migrations.

## 5. Volumes

Persistent:
- PostgreSQL;
- model/backtest artifacts;
- backups;
- reverse-proxy certificates if applicable.

Redis persistence optional based on queue design; jobs must be recoverable/idempotent from DB.

## 6. Backup

Daily DB backup + configurable retention. Include restore test procedure. Backups contain strategy/model metadata and paper ledger; treat them as sensitive.

## 7. Deploy workflow

Recommended:
- main branch protected;
- CI lint/test/build;
- tag/release image;
- server pulls approved revision;
- database backup;
- migrate;
- restart services;
- readiness check;
- rollback application image if health fails (DB rollback only with explicit migration plan).

A simple `scripts/deploy.sh` can wrap this for a single VPS.

## 8. Schedules

Use `Asia/Tehran` market calendar service, not host-local naive cron assumptions.

Jobs:
- pre-session instrument/rule sync;
- during-session market ingestion;
- periodic feature/signal updates;
- post-session EOD reconciliation;
- nightly feature/backtest maintenance;
- Codal poll continuously at a compliant cadence;
- daily backup/data-health report.

Unexpected market closure must stop unnecessary fast polling.

## 9. Resource controls

- bounded HTTP concurrency;
- worker queue limits;
- DB connection pool limits;
- query indexes/retention policies;
- backtests in separate worker queue so they cannot starve live analysis.

## 10. Graceful degradation

If ML worker fails, deterministic strategies continue.
If Codal unavailable, price/flow strategies can continue with a visible fundamental/event freshness penalty.
If primary market feed is stale, stop publishing new actionable signals.

## 11. Time sync

Server clock must use NTP. Alert on material clock drift because timestamp ordering affects point-in-time correctness.
