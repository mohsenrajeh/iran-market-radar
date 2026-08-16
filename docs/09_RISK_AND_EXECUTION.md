# 09 — Risk Engine, Entry/Exit and Paper Execution

## 1. Risk engine precedes execution

A high alpha score does not authorize a trade. Risk gating returns:
- `approved`;
- `approved_with_reduced_size`;
- `blocked` + reason codes.

## 2. Eligibility gates

Default configurable gates:
- instrument currently tradable/eligible;
- data fresh enough;
- minimum average daily value/volume;
- minimum history;
- not excluded market/board/instrument class;
- no unresolved corporate-action data issue;
- not in extreme queue/no-fill condition unless strategy specifically models it;
- opportunity score/probability/confidence above thresholds;
- expected edge > estimated costs + safety margin.

## 3. Position sizing

Phase 1 produces a suggested size for paper trading only.

Supported methods:
- fixed fractional capital;
- volatility targeting;
- risk-per-trade based on stop distance;
- liquidity/capacity cap;
- sector concentration cap.

Default formula concept:

```text
risk_budget = NAV * risk_per_trade_pct
stop_risk_per_share = abs(entry - stop)
size_by_risk = risk_budget / stop_risk_per_share
size = min(size_by_risk, max_notional_pct_NAV, liquidity_capacity)
```

Use Iranian currency/unit conventions carefully and test integer rounding/tick/order constraints.

No Kelly sizing in production v1.

## 4. Portfolio constraints

Configurable:
- max open positions;
- max gross exposure;
- max position % NAV;
- max sector exposure;
- correlated-position penalty;
- max daily/new-position risk;
- max drawdown before risk-off;
- max strategy exposure.

## 5. Entry models

Each order intent has:
- desired price/zone;
- max chase/slippage;
- expiration;
- fill-or-cancel behavior concept;
- participation cap;
- rationale.

Paper engine simulates fills using the same rules as backtest.

## 6. Exit state machine

Once a paper position is open, evaluate:
1. hard invalidation/stop;
2. material adverse event;
3. target/trailing rule;
4. strategy reversal/edge decay;
5. time stop;
6. portfolio/risk kill-switch.

If multiple triggers fire, record precedence and reason.

## 7. Stop-loss semantics in price-limited markets

A stop is an **exit intent**, not a guarantee of fill. If price gaps/locks at lower limit, the paper/live layer records `stop_triggered_pending_fill`, and realized loss can exceed theoretical stop. UI must communicate this.

## 8. Paper broker

Implement full broker-like state machine:
- cash;
- buying power;
- pending orders;
- partial fills;
- rejected/expired orders;
- positions and average price;
- realized/unrealized P&L;
- fees/taxes;
- corporate-action effects where required.

Paper trading should run continuously from live signals so later broker integration can compare behavior.

## 9. Future live safety controls

Mandatory before live adapter promotion:
- idempotency key per intent/order;
- duplicate order protection;
- max notional per order/day;
- max orders per minute;
- stale-data kill switch;
- broker connectivity kill switch;
- portfolio reconciliation against broker truth;
- manual global kill switch;
- audit log;
- alert on reject/partial-fill mismatch;
- fail closed on unknown order state.

## 10. Reconciliation

When broker exists, broker positions/cash are source of truth for live account. Internal ledger is reconciled at startup and periodically. Never blindly send compensating trades on reconciliation mismatch.
