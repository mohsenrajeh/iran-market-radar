# 14 — Test Plan

## 1. Unit tests

### Market data mapping
Golden fixtures from documented source responses. Verify IDs, prices, timestamps, nulls, Persian normalization.

### Features
Hand-computed fixtures for returns, ATR, momentum, client-flow, volume z-score, breadth, fundamental growth.

### Strategies
Small deterministic datasets with expected candidate/no-candidate outcomes and exact reason codes.

### Scoring/calibration
- probability remains in [0,1];
- score/confidence in [0,100];
- tiny sample shrinks probability/confidence;
- calibration trained only from provided held-out predictions;
- opportunity score components reconcile.

### Risk
- stop distance zero/negative rejected;
- position size respects all caps;
- stale data blocks;
- illiquid/unsupported instruments block;
- duplicate intent is idempotent.

## 2. Property/invariant tests

Critical invariants:
- adding a future row cannot change a feature at a past timestamp;
- incremental feature result equals full recompute;
- no backtest fill before order creation;
- cash/position ledger balances after fills/fees;
- total filled quantity never exceeds order quantity;
- no trade during halt;
- price outside effective allowed range cannot fill;
- raw prices never modified by adjustment job.

## 3. Integration tests

Use recorded/fixture source adapters:
- ingest -> canonical DB -> features -> strategy -> score -> API;
- filing publication -> feature update -> event strategy;
- data stale -> opportunity publication blocked;
- paper order -> partial/full fill -> position -> exit.

## 4. Backtest regression tests

Create small synthetic market with known outcomes including:
- normal fills;
- upper-limit no-fill;
- lower-limit stop unable to fill;
- halt;
- capital action;
- missing session;
- partial fill.

Expected trade ledger must be exact.

## 5. Leakage tests

Build sentinel features where future data is deliberately distinguishable. Tests should fail if pipeline accidentally sees it. Check filing `available_at` and label overlap purge.

## 6. API tests

- auth/roles;
- validation;
- pagination;
- filtering/sorting;
- error envelopes;
- OpenAPI schema.

## 7. UI/Playwright

Critical flows:
- login;
- view opportunity list;
- distinguish score/probability/confidence labels;
- open symbol detail;
- launch/view backtest;
- approve paper trade;
- stale-data banner;
- RTL layout sanity.

## 8. Load tests

Simulate realistic universe/snapshot rates. Verify:
- ingestion remains within source limits;
- DB query p95;
- feature batch time;
- dashboard unaffected by a running backtest.

## 9. Release gate

CI must fail on:
- unit/integration test failure;
- type/lint failure;
- migration divergence;
- known critical dependency vulnerability where fix exists;
- coverage drop below chosen threshold for domain modules;
- golden backtest regression mismatch.
