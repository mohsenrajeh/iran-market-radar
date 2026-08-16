# 20 — Final Phase-1 Acceptance Criteria

Phase 1 is not complete until all are true:

## Data
- [ ] Official/authorized TSETMC adapter implemented from current docs.
- [ ] Instrument master, historical EOD and current market data persist idempotently.
- [ ] At least client-type and order-book adapters are implemented when current source entitlement exposes them, otherwise capability is reported unavailable rather than faked.
- [ ] Data freshness/completeness visible in UI.
- [ ] Corporate actions/raw-vs-adjusted handling tested.
- [ ] Trading sessions/halts/dynamic limits represented.

## Analysis
- [ ] Core deterministic strategies S01–S09 run across eligible universe.
- [ ] Strategy votes/reasons stored and visible.
- [ ] Entry/invalidation/exit proposal generated.
- [ ] Market regime and sector ranking computed.

## Quantitative trust
- [ ] Walk-forward backtester operational.
- [ ] No same-bar look-ahead fills.
- [ ] Price-limit/queue/no-fill simulation present.
- [ ] Costs/slippage/participation modeled.
- [ ] `p_profit` calibrated from OOS predictions/signals.
- [ ] Brier/reliability metrics stored.
- [ ] Score/probability/confidence are distinct in API/UI.
- [ ] Experiment registry prevents silent parameter mining.

## ML
- [ ] Baseline + tree model training pipeline can run if sufficient history exists.
- [ ] ML promotion requires OOS and calibration report.
- [ ] ML failure does not stop deterministic strategies.

## Product
- [ ] Persian RTL dashboard includes market, opportunities, symbol detail, strategies, backtests, paper portfolio and data health.
- [ ] No-quality-opportunity state is supported.
- [ ] Stale-data state blocks actionable publication.

## Paper execution
- [ ] Risk engine and position sizing operate.
- [ ] Partial fill/stop pending/no-fill states supported.
- [ ] Ledger invariants tested.
- [ ] Kill switch works.

## Deployment
- [ ] Docker Compose production startup documented.
- [ ] Secrets not committed.
- [ ] Daily backup and restore procedure tested.
- [ ] CI tests/lint/build pass.
- [ ] App can recover from source/network restart without duplicate corruption.

## Live trading
- [ ] `LIVE_TRADING_ENABLED` remains false.
- [ ] No undocumented broker endpoints or browser automation are present.
- [ ] Authorized BrokerAdapter contract is ready for later implementation.
