# 15 — Implementation Roadmap

Implement in milestones. Each milestone must leave the repo runnable and tested.

## M0 — Repository foundation

Deliver:
- monorepo structure;
- Docker Compose;
- FastAPI + Next.js skeleton;
- Postgres/Redis;
- Alembic;
- typed settings;
- auth/admin bootstrap;
- health endpoints;
- CI lint/test/build;
- `.env.example`;
- structured logging.

Acceptance: clean Docker startup and protected dashboard shell.

## M1 — Canonical market data

- implement source adapter interface;
- implement official TSETMC REST adapter after reading current docs;
- instrument master;
- EOD backfill;
- market snapshots/current state;
- trading sessions/status;
- effective market rules/thresholds;
- checkpoints/idempotency/data-quality metrics.

Acceptance: selected backfill range can be re-run with no duplicate corruption; data-health page reports completeness/freshness.

## M2 — Intraday/client-flow data

When source/entitlement supports:
- intraday snapshots/bars;
- order-book depth;
- client type;
- index/sector series;
- retention/compression plan.

Acceptance: live collector runs for a session with bounded requests and no drift/duplicate growth.

## M3 — Feature engine + regime

Implement core price/trend/volume/liquidity/sector/client-flow features and market regime. Add feature versioning and point-in-time tests.

Acceptance: full and incremental feature computation match for fixtures and historical slices.

## M4 — Deterministic strategies

Implement S01–S09 core candidates before ML:
- momentum/RS;
- trend;
- breakout;
- pullback;
- selective reversion;
- volume anomaly;
- client flow;
- order-book experimental if data adequate;
- sector rotation.

Acceptance: candidate explanations and entry/invalidation/exit proposals persisted.

## M5 — Backtest engine

Implement:
- walk-forward compatible simulation;
- point-in-time universe;
- fees/slippage;
- halts;
- dynamic price limits;
- queue/no-fill conservative model;
- participation limits;
- detailed metrics/reports.

Acceptance: synthetic execution regression suite passes exactly.

## M6 — Calibration + opportunity scorer

- empirical deterministic strategy calibration;
- p_profit buckets with shrinkage;
- confidence computation;
- signal strength;
- ensemble opportunity score;
- grades;
- OOS metrics API/UI.

Acceptance: UI clearly separates probability, score and confidence; calibration report available.

## M7 — Codal/fundamental

- SEDRA adapter when credentials available;
- filing/fact/corporate action schema;
- fundamental features;
- fundamental quality/value;
- monthly sales momentum;
- event strategy;
- optional NLP summarization/extraction.

Acceptance: corrected/restated filing cannot leak backward in time.

## M8 — ML ranker

- point-in-time training dataset builder;
- regularized baseline;
- tree-based candidate models;
- rolling training/OOS prediction store;
- hyperparameter discipline/experiment registry;
- calibration;
- champion/challenger.

Acceptance: model only promoted with reproducible OOS report and calibration diagnostics.

## M9 — Full dashboard

- market overview;
- opportunities;
- symbol detail;
- sectors;
- strategy lab;
- backtests;
- data health;
- settings;
- responsive RTL polish.

## M10 — Paper trading

- broker-like paper ledger;
- risk engine;
- position sizing;
- entry/partial-fill/exit state machine;
- performance vs predicted outcomes;
- kill switch.

Acceptance: can run unattended in paper mode without corrupting ledger.

## M11 — Production hardening

- backups/restore drill;
- observability;
- alerting;
- load testing;
- NTP/time checks;
- deployment script;
- security review;
- operations runbook.

## M12 — Future broker integration (separate approval)

Only after an authorized API is obtained:
- implement one `BrokerAdapter`;
- sandbox/test account if available;
- order/portfolio reconciliation;
- idempotency;
- rejects/partial fills;
- live risk limits;
- tiny-capital supervised pilot;
- only then consider unattended automation.

Do not block M0–M11 on broker availability.
