# 05 — Feature Engineering

## Principle
Indicators are features, not proof of edge. Every feature must be deterministic, timestamp-safe, versioned and testable. Compute features only from data available at `as_of`.

## 1. Price and return features

For multiple lookbacks (e.g. 1, 3, 5, 10, 20, 60, 120, 250 trading sessions where history permits):
- log/simple returns;
- gap return;
- close-to-close, open-to-close, overnight return when timestamps support it;
- distance from rolling high/low;
- rolling drawdown;
- rolling volatility (std, EWMA, robust MAD variants);
- ATR / normalized ATR;
- range expansion/compression;
- realized skew/kurtosis with minimum sample gates;
- downside/upside volatility;
- return autocorrelation as diagnostic, not necessarily a primary signal.

## 2. Trend/momentum

- moving-average slopes normalized by volatility;
- EMA/SMA relationships;
- regression slope and R² over multiple windows;
- time-series momentum sign/strength;
- cross-sectional momentum percentile;
- residual momentum after market/sector return removal;
- relative strength vs market index and sector index;
- 52-week / 250-session high proximity;
- breakout distance and breakout confirmation volume.

Use RSI/MACD/Stochastic only as supporting standardized features. Do not create a strategy named simply `rsi_buy` as a core production strategy.

## 3. Volume/liquidity

- turnover and turnover percentile;
- volume/value relative to rolling median/mean;
- robust volume z-score;
- Amihud-like illiquidity proxy where valid;
- zero-trade days / stale-session ratio;
- average daily value traded;
- participation capacity estimate;
- spread/bid-ask features where snapshots exist;
- depth imbalance;
- order-count imbalance;
- price impact proxy;
- queue concentration near allowed limits;
- days locked at upper/lower price limit;
- estimated executable notional.

## 4. Iranian client-type / حقیقی-حقوقی features

If source provides raw counts/volumes/values:
- real buy per-capita value;
- real sell per-capita value;
- ratio/log-ratio of real buy vs sell per capita;
- net real money flow;
- legal net flow;
- real participation share;
- persistence over 3/5/10 sessions;
- z-scores relative to symbol history;
- sector-relative real flow;
- divergence: price down + strong real accumulation; price up + heavy real distribution.

Guard divisions by small counts and winsorize extreme ratios. Raw and transformed values must both be inspectable.

## 5. Order-flow / order-book features

Only if authorized, reliable snapshots exist:
- top-N depth imbalance;
- microprice proxy;
- spread in ticks and bps;
- weighted bid/ask depth;
- replenishment/cancellation rates when event cadence supports them;
- short-window order-flow imbalance;
- queue growth/decay at price limits;
- estimated probability of fill using historical queue outcomes.

Do not pretend a 10-second snapshot feed is tick data.

## 6. Sector and market breadth

- percentage of universe positive/negative;
- percentage above 20/50/100-session moving averages;
- new highs/new lows;
- median cross-sectional return;
- equal-weight vs cap-weight divergence;
- sector relative return/momentum;
- sector breadth;
- sector turnover/flow acceleration;
- concentration of market gains/losses;
- upper/lower price-limit breadth;
- advance/decline style metrics.

## 7. Fundamental features

Point-in-time and sector-aware:
- revenue/sales growth YoY and MoM where meaningful;
- rolling 3m/6m sales acceleration;
- gross/operating/net margin and changes;
- EPS/earnings growth;
- cash-flow quality if available;
- leverage/debt ratios;
- ROE/ROA/ROIC style quality metrics;
- valuation ratios (P/E, P/S, P/B, EV-based when facts support it);
- valuation percentile within sector and history;
- accrual/quality proxies;
- earnings/sales surprise vs the company's own seasonality and rolling baseline.

Never compare raw P/E across sectors without context. Negative/undefined denominators must be handled explicitly, not replaced by zeros.

## 8. Filing/event features

From Codal/SEDRA structured parser and optional NLP:
- days since latest monthly report;
- monthly sales surprise z-score;
- filing amendment/correction flag;
- material disclosure category and polarity;
- capital increase stage/type;
- dividend/AGM timing;
- contract/production event tag;
- filing frequency anomaly;
- publication during/after market session.

NLP-derived fields have confidence/provenance and cannot overwrite structured facts.

## 9. Regime features

- index trend/volatility;
- breadth trend;
- cross-sectional dispersion;
- market turnover/liquidity;
- lower-limit/upper-limit concentration;
- sector concentration;
- shock indicators from large gaps/closures;
- optional macro proxy returns.

## 10. Feature standardization

For cross-sectional models:
- winsorize by training-period rules;
- sector-neutralize selected factors where justified;
- robust z-score/percentile rank;
- fit transformations on training data only.

Do not calculate normalization parameters using the entire future dataset.

## 11. Missing data

Each feature includes missingness semantics. ML models receive missing flags where useful. A missing filing value is not zero. Signals with key missing features can degrade confidence or become ineligible.

## 12. Feature tests

For every feature:
- fixture with hand-calculated expected result;
- invariant for no future timestamps;
- edge cases: halted days, zero volume, capital action, missing sessions;
- incremental computation equals full recomputation;
- no NaN/inf leakage to scoring without explicit handling.
