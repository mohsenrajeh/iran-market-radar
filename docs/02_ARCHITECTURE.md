# 02 — System Architecture

## 1. High-level flow

```text
Official/Authorized Sources
  TSETMC REST ───────────┐
  Codal/SEDRA ───────────┤
  Optional macro/news ───┤
                        ▼
                 Ingestion Adapters
                        ▼
               Canonical Data Layer
                        ▼
        Data Quality + Market Rule Resolver
                        ▼
                 Feature Engine
                        ▼
    ┌──────── Strategy Registry ────────┐
    │ technical / flow / fundamental   │
    │ event / sector / ML ranker       │
    └───────────────────────────────────┘
                        ▼
              Candidate Signal Store
                        ▼
             Calibration + Ensemble
                        ▼
                  Risk / Eligibility
                        ▼
              Published Opportunities
                  ├── REST/WebSocket API
                  ├── Persian Dashboard
                  └── Paper Execution
                            ▼
                    Future Broker Gateway
```

## 2. Service boundaries

### API service
FastAPI; authentication; read APIs; admin actions; backtest launch; paper-trade approval; WebSocket/SSE for updates.

### Collector service
- source adapters;
- rate-limited HTTP clients;
- canonical mapping;
- incremental sync checkpoints;
- retries/backoff;
- raw payload archival for critical source entities where permitted;
- idempotent upsert.

### Scheduler/worker
Celery worker + scheduler/beat. Separate queues:
- `ingest_fast`;
- `ingest_slow`;
- `features`;
- `strategies`;
- `backtests`;
- `nlp`;
- `maintenance`.

### Feature engine
Deterministic transformations from canonical data to point-in-time feature snapshots. Supports incremental and full rebuild.

### Strategy engine
Plugin registry. Every strategy declares:
- required features;
- supported instrument classes;
- supported horizons;
- minimum history/data quality;
- parameters;
- raw score semantics;
- entry/invalidation/exit model.

### Calibration/scoring service
- produces OOS probability maps/calibrators;
- strategy reliability statistics;
- ensemble combination;
- current cross-sectional ranking.

### Backtester
Event/bar simulator sharing the same strategy, feature and market-rule code as production where possible.

### Paper broker
Portfolio/cash/orders/fills ledger with realistic simulated execution.

### Broker gateway
Interface only in phase 1. Authorized adapters later.

## 3. Storage

### PostgreSQL
Source of truth for:
- instrument master;
- EOD bars;
- canonical events;
- features;
- strategies/signals;
- models/calibration;
- backtests;
- paper trades;
- configuration/audit.

### TimescaleDB (preferred extension)
Use hypertables for high-volume intraday data if extension is available:
- market snapshots/bars;
- order-book snapshots;
- intraday client-type snapshots;
- index snapshots.

Application must not rely on Timescale-only SQL for essential correctness without a plain-Postgres fallback.

### Redis
- queue broker/result backend;
- short-lived cache;
- distributed locks;
- signal update pub/sub.

### Object artifacts
Backtest reports/model binaries can initially live on a Docker volume with DB metadata. Optional S3/MinIO adapter later.

## 4. Canonical time model

Store all timestamps as timezone-aware UTC in database and carry source-local date/time fields where needed. User display uses `Asia/Tehran` and Jalali formatting as a presentation concern.

Each analytical record must distinguish:
- `event_time`: when the market/company event occurred;
- `available_at`: earliest timestamp the system could legitimately know it;
- `ingested_at`: when our collector received it.

Backtests use `available_at` to prevent leakage.

## 5. Raw vs adjusted prices

Never overwrite raw source prices.

Store:
- raw OHLC/close/last;
- adjustment factors/version;
- adjusted analytical series generated from corporate actions;
- point-in-time adjustment metadata.

Signals displayed for current execution use raw executable prices. Return-history features may use adjusted series when appropriate.

## 6. Dependency direction

Domain modules must not import infrastructure clients.

```text
Domain <- application/services <- infrastructure/adapters
```

Strategies depend on domain feature interfaces, not directly on TSETMC HTTP clients or SQLAlchemy sessions.

## 7. Idempotency and checkpoints

Every collector has a stable uniqueness key and checkpoint. Examples:
- EOD: `(instrument_id, trading_date)`;
- snapshot: `(instrument_id, source_timestamp, snapshot_kind)`;
- filing: source announcement ID;
- corporate action: source ID + event version.

Re-running the same window must produce the same canonical records.

## 8. Cache strategy

Precompute current opportunities in DB and cache query results briefly. The UI does not trigger full-market recomputation. Strategy recomputation is job-driven.

## 9. Failure modes

### Source unavailable
- keep last known data but mark stale;
- do not publish new actionable signals above stale threshold;
- emit data-health alert.

### Partial instrument failure
- quarantine symbol/feature set;
- continue market scan;
- lower data-quality/executability.

### Database/queue outage
- fail closed for any future execution;
- preserve idempotency on restart.

### Model artifact missing
- disable affected model strategy;
- deterministic strategies continue.

## 10. Versioning

Version/hash:
- market data schema;
- feature definitions;
- strategy code + parameters;
- model artifact;
- calibration artifact;
- market-rule set;
- transaction-cost model.

Every published signal references these versions.
