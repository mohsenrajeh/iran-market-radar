# 10 — API Contracts

Prefix: `/api/v1`

Use typed Pydantic schemas, OpenAPI and pagination. All timestamps ISO-8601 with timezone. Persian strings are UTF-8.

## 1. Market overview

### `GET /market/overview?horizon=5d`
Returns:
- session status;
- indices;
- breadth;
- turnover/liquidity;
- regime;
- sector rankings;
- count of A/B opportunities;
- data freshness/health.

### `GET /market/sectors`
Sector scorecard: momentum, breadth, flow, turnover, opportunity count.

## 2. Opportunities

### `GET /opportunities`
Filters:
- horizon;
- min score/p_profit/confidence;
- strategy;
- market/sector;
- liquidity;
- grades;
- actionable only;
- sort.

Response item matches `schemas/signal.schema.json`.

### `GET /opportunities/{signal_id}`
Full evidence:
- component votes;
- feature snapshot;
- model/calibration stats;
- entry/exit plan;
- related filings/events;
- comparable historical OOS bucket performance.

### `GET /opportunities/stream`
SSE/WebSocket for newly published/invalidated/materially changed signals.

## 3. Symbols

### `GET /symbols`
Search by ticker/name/ISIN.

### `GET /symbols/{id}`
Reference data + current status.

### `GET /symbols/{id}/chart`
Bars with selected adjustment mode and overlays returned as data, not pre-rendered image.

### `GET /symbols/{id}/features`
Current and historical selected features.

### `GET /symbols/{id}/signals`
Signal history and outcomes.

### `GET /symbols/{id}/filings`
Point-in-time filings/events.

## 4. Strategies

### `GET /strategies`
Status, horizons, current version, OOS metrics, calibration quality.

### `GET /strategies/{key}`
Configuration schema and diagnostics.

### `PATCH /strategies/{key}`
Admin-only enable/disable/config updates with audit log. Updates create new config version; never mutate historical run config.

## 5. Backtests

### `POST /backtests`
Launch with immutable config.

### `GET /backtests/{id}`
Status + summary metrics.

### `GET /backtests/{id}/equity`
Equity/drawdown series.

### `GET /backtests/{id}/trades`
Auditable trade list.

### `GET /backtests/{id}/report`
Fold/regime/sector/calibration/execution diagnostics.

## 6. Paper trading

### `GET /paper/portfolio`

### `POST /paper/orders/from-signal/{signal_id}`
Creates risk-checked intent; default user confirmation flow.

### `GET /paper/orders`

### `GET /paper/positions`

### `POST /paper/kill-switch`
Admin action; audit logged.

## 7. Data health

### `GET /health`
Application liveness/readiness.

### `GET /data/health`
Per-source freshness/completeness/error stats.

### `POST /data/backfill`
Admin-only bounded backfill job.

### `GET /jobs/{id}`
Job status.

## 8. Settings

### `GET /settings/market-rules`
Current effective rule configuration and source references.

### `GET /settings/risk`

### `PATCH /settings/risk`
Versioned + audited.

## 9. Error envelope

```json
{
  "error": {
    "code": "STALE_MARKET_DATA",
    "message_fa": "داده بازار برای انتشار سیگنال جدید به‌روز نیست.",
    "details": {},
    "request_id": "..."
  }
}
```

## 10. Auth

Single-user deployment may start with admin account, but implement roles:
- `viewer`;
- `researcher`;
- `trader` (paper approval);
- `admin`.

Future live-trader permission is distinct and cannot be implied by admin UI login alone.
