# 04 — Canonical Data Model

Use UUID internal IDs, UTC timestamps, effective-dated metadata, and database constraints. This is a logical schema; Codex may normalize further.

## 1. Reference tables

### `instrument`
- `id`
- `source_instrument_code`
- `isin`
- `ticker`
- `ticker_normalized`
- `name_fa`
- `instrument_class`
- `market`
- `board`
- `sector_id`
- `company_id`
- `listed_at`, `delisted_at`
- `is_active`
- `metadata_json`

Indexes: ISIN, source code, normalized ticker, market/sector.

### `instrument_alias`
Historical ticker/name mappings with validity timestamps.

### `sector`
Official sector/group mapping plus optional hierarchy.

### `trading_session`
- market/session date;
- open/close/auction timestamps;
- status;
- source evidence.

### `market_rule_set`
Effective-dated transaction/trading rules.

## 2. Market data

### `eod_bar`
Unique `(instrument_id, trading_date)`:
- raw open/high/low/close/last;
- previous close;
- volume/value/trades;
- allowed min/max if available;
- base volume if relevant;
- instrument status;
- adjustment factor reference;
- source timestamps.

### `intraday_bar`
Configurable 1m/5m/etc bars derived from authorized snapshots/trades. Store bar construction version.

### `market_snapshot`
- last/close/bid/ask;
- volume/value/trades;
- day high/low;
- thresholds;
- status;
- source timestamp.

### `orderbook_snapshot`
Top N levels:
- bid prices/sizes/order counts;
- ask prices/sizes/order counts;
- spread;
- source timestamp.

For scale, use normalized child rows or compact JSONB depending query profile; preserve deterministic representation.

### `client_type_snapshot`
- real buy count/volume/value;
- real sell count/volume/value;
- legal buy/sell equivalents;
- derived per-capita values are features, not canonical raw fields unless source directly provides them.

### `index_bar`
Market/sector/index OHLC/returns/volume where supplied.

## 3. Corporate/fundamental

### `filing`
- source ID;
- instrument/company;
- title/type/category;
- period metadata;
- published_at;
- amended_from_id;
- URL/reference;
- structured fields JSON;
- raw text/document metadata;
- parse status.

### `fundamental_fact`
Point-in-time fact model:
- company/instrument;
- fact key;
- numeric/text value;
- unit;
- period start/end;
- published_at/available_at;
- filing_id;
- restatement version.

### `corporate_action`
Dividend, capital increase, rights, split-like adjustment event, ticker changes, etc.; effective-dated and source-referenced.

## 4. Analytical tables

### `feature_definition`
- stable key;
- version;
- formula description;
- inputs;
- lookback;
- timestamp semantics.

### `feature_snapshot`
Long or hybrid wide store:
- instrument;
- as_of;
- horizon/context;
- feature_set_version;
- feature values;
- data_quality score.

For performance, a wide materialized feature table per feature-set version is acceptable while retaining definitions/versioning.

### `market_regime`
- as_of;
- regime label;
- probabilities/scores;
- feature summary;
- model/version.

### `strategy_definition`
- key/version;
- parameter schema;
- enabled;
- supported universe/horizons.

### `strategy_run`
Immutable run metadata with code/config/data version hashes.

### `strategy_candidate`
One strategy's candidate:
- raw score;
- expected edge if strategy produces one;
- entry/invalidation/exit proposal;
- reason codes;
- feature evidence.

### `published_signal`
Canonical user-facing opportunity:
- instrument/as_of/horizon;
- `p_profit`;
- `confidence`;
- `signal_strength`;
- `opportunity_score`;
- expected return/drawdown;
- execution levels;
- regime/liquidity/data quality;
- status/expiry;
- all version references.

### `signal_component`
Per-strategy contribution/vote/reason so the ensemble is explainable.

## 5. ML and calibration

### `model_registry`
- model key/version/type;
- training interval;
- feature set;
- hyperparameters;
- artifact URI/hash;
- metrics;
- status (candidate/champion/retired).

### `calibration_model`
- target horizon;
- predictor/model version;
- calibration method;
- training/OOS period;
- Brier/log-loss/reliability stats;
- artifact/hash.

## 6. Backtest

### `backtest_run`
- immutable config JSON/hash;
- code/data/strategy/model versions;
- start/end;
- universe definition;
- cost/fill model;
- status;
- metrics.

### `backtest_order`, `backtest_fill`, `backtest_position`, `backtest_equity_curve`
Store enough detail to audit every simulated trade.

### `experiment_registry`
Track every strategy/model experiment to reduce silent parameter mining.

## 7. Paper/live-ready execution

### `portfolio`
Paper now; broker-linked later.

### `order_intent`
Risk-approved desired action before broker-specific translation.

### `broker_order`
External/internal IDs, state transitions and idempotency key.

### `fill`
Execution record.

### `position`
Current/closed positions.

### `risk_event`
Kill-switch, limit breach, stale-data block, duplicate-order prevention event.

## 8. Operational/audit

- `ingestion_checkpoint`
- `data_quality_event`
- `job_run`
- `source_health`
- `audit_log`
- `app_setting`
- `user` / `role`

## 9. Retention

- EOD/reference/fundamental: indefinite.
- Intraday snapshots/order book: configurable compression/retention, but preserve enough history for chosen backtests.
- Raw HTTP payloads: retain selectively for reproducibility/compliance and avoid unnecessary storage of immutable duplicates.
