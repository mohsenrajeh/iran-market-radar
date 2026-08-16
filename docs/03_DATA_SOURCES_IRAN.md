# 03 — Iran Market Data Sources and Ingestion Policy

Verified/known source landscape as of 2026-08-12. The implementation must re-check live documentation during build/deployment because endpoints, authentication and entitlements can change.

## 1. TSETMC official REST web service — primary market-data source

The Securities and Exchange Organization announced the new TSETMC web service in late 2025. The new service uses REST; new development is intended for this REST platform while the older SOAP service remains supported for a transition period. Official documentation is referenced at:

- https://api.tsetmc.com/docs/
- SEO announcement: https://service.seo.ir/news/93205

### Adapter requirements

Create `TsetmcRestAdapter` behind a source interface. Do not hard-code endpoint guesses from unofficial libraries. During implementation:

1. inspect current official docs;
2. document authentication/entitlement requirements;
3. map official fields to canonical names;
4. store source field name in mapping tests;
5. respect documented request limits;
6. use conditional/backoff retry, not aggressive scraping.

### Data categories to obtain if exposed by entitlement

- instrument master: codes, ISIN, names, market, board, sector, status;
- current market watch/snapshots;
- EOD price/volume/value/trade count;
- intraday trades/bars or snapshots;
- static thresholds / allowed price range;
- best bid/ask/order-book depth;
- client type / حقیقی-حقوقی statistics;
- index/sector series;
- market status and supervisor messages;
- shareholders/ownership metadata where appropriate;
- corporate-action/reference data needed for adjustment.

### Ingestion cadence

Cadence is configurable and bounded by the authorized service:

- instrument master: before session + daily reconciliation;
- market status/rules: pre-session and on observed changes;
- full market watch: 5–15 seconds during market session if allowed;
- top-of-book/depth: prioritize eligible/liquid universe; 3–15 seconds if allowed;
- client-type snapshots: source-appropriate cadence;
- EOD reconciliation: after session and nightly retry;
- historical backfill: throttled background queue.

Never create a request storm across every symbol if a bulk endpoint exists.

## 2. Codal / SEDRA — fundamental and event data

Codal's operator (Rayan Bourse) describes SEDRA data services as REST API web services. Reference:

- https://my.codal.ir/fa/statement/540929/

Use an `SedraAdapter` when credentials/service access are available.

### Required event classes

- monthly activity/sales reports;
- quarterly/interim/annual financial statements;
- material information disclosures (الف/ب or current equivalents);
- capital increase notices and stages;
- AGM/EGM notices/results;
- dividend-related disclosures;
- contracts/production/sales events when structured;
- clarifications/suspension-related disclosures.

### Point-in-time rule

A filing feature becomes available at the **publication timestamp**, never at its financial period end date. Corrections/amendments create a new version; do not rewrite history as if the corrected document existed earlier.

## 3. Optional public/authorized auxiliary sources

Keep adapters modular and disabled by default:
- macro FX/gold/rates/commodity proxies from licensed/reliable sources;
- company news feeds;
- sector commodity prices (oil, metals, petrochemicals) where legal and useful;
- Persian sentiment feeds.

No source can silently override official market prices.

## 4. Data-quality model

For each source/table track:
- freshness delay;
- completeness ratio;
- duplicate ratio;
- null/invalid-field rate;
- sequence gaps;
- cross-source reconciliation discrepancy;
- source HTTP error rate;
- last successful checkpoint.

Calculate a `data_quality_score` 0–100 for each symbol/time. Signals below a configurable minimum cannot be published as actionable.

## 5. Canonical instrument identity

Never use Persian ticker alone as primary key because symbols can change/collide. Prefer stable official codes/ISIN. Keep aliases/history:
- internal UUID;
- `instrument_id/source_code`;
- ISIN;
- current ticker;
- normalized ticker;
- historical ticker aliases;
- company/legal entity relation where available.

## 6. Persian normalization

Canonical text pipeline:
- Arabic/Persian Yeh/Kaf normalization;
- zero-width/non-breaking whitespace handling;
- trim control characters;
- retain original raw text;
- normalized ticker/name for search only.

Do not normalize numeric source identifiers.

## 7. Trading calendar

Build a market calendar from observed sessions/official market status rather than assuming Saturday–Wednesday forever. Support:
- holidays;
- unexpected closures;
- shortened/changed sessions;
- symbol-level halts/reopenings.

Backtesting uses actual tradable sessions.

## 8. Market rules

Price limits, tick sizes, fee/tax schedules, base-volume rules, board-specific constraints and order limits can change. Represent them with effective-dated records:

```text
market_rule_set
  effective_from
  effective_to
  market/board/instrument_class
  rule_type
  value/json
  source_reference
```

Prefer per-instrument dynamic thresholds from official data for actual execution simulation.

## 9. Source compliance

- Respect source terms/licensing.
- Cache rather than re-download immutable history.
- Identify our client if required by service policy.
- Never bypass paywalls/authentication/rate limits.
- Broker data access later must be authorized.

## 10. Fallback policy

A fallback adapter may exist for development/demo fixtures, but production should not silently fall back from an official authenticated service to brittle HTML scraping. If the primary source fails, surface degraded state.
