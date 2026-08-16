# 08 — Backtesting and Validation

## 1. Goal

The backtester is not a marketing chart. It must estimate whether a strategy had executable, stable, out-of-sample edge under Iranian market constraints.

## 2. Shared-code rule

Production and backtest must share:
- feature definitions;
- strategy logic;
- market-rule resolver;
- cost model;
- order intent definitions.

Avoid a separate “easy” research implementation that cannot match production signals.

## 3. Time split

Never random-split time series.

Default walk-forward scheme:

```text
Train:      expanding or rolling multi-year window
Validation: next N months
Test/OOS:   following N months
Roll forward
```

Parameters depend on available history/horizon. Store every window definition.

For overlapping labels, use purge/embargo around folds so future outcome windows do not leak between train and validation/test.

## 4. Point-in-time fundamental data

Use `available_at`. Restated filings must not rewrite past features. If point-in-time history cannot be reconstructed, mark that feature unavailable for historical validation rather than leaking corrected numbers.

## 5. Survivorship

Universe for a historical date is the instruments that existed/qualified then, not today's active list. Include delisted/suspended instruments where data permits.

## 6. Signal-to-fill timing

If a signal uses end-of-day close information at T:
- earliest default fill is next tradable session, never the same close;
- use next open/marketable modeled price or next bar according to strategy;
- apply price-limit and halt logic.

For intraday signals, fill occurs on a strictly later source timestamp/bar.

## 7. Iranian execution constraints

### Price limits
Use actual effective rules/static thresholds where available. Orders outside allowed range cannot fill.

### Queue/no-fill
When price is locked at upper/lower limit:
- do not assume fill simply because historical OHLC touched the limit;
- estimate fill from subsequent traded volume, queue/depth snapshots if available, order position assumptions and participation rules;
- if data is insufficient, use conservative “unfilled” or sensitivity scenarios.

### Halts
No fill while instrument non-tradable. Strategy clock may use trading sessions rather than calendar days.

### Liquidity/participation
Default order size cannot consume an unrealistic share of traded volume. Use configurable max participation by notional/ADV and simulate slippage increasing with participation.

### Fees/taxes
Effective-dated configuration. Never bake a current percentage into strategy code.

## 8. Slippage model

Start with conservative tiered model based on spread + volatility + participation + queue state. Later fit empirical model from paper/live fills.

Store gross and net results separately.

## 9. Metrics

For each strategy/horizon/regime and portfolio:
- total/annualized return where meaningful;
- max drawdown;
- Sharpe/Sortino with caveats;
- Calmar;
- win rate;
- average/median win/loss;
- payoff ratio;
- expectancy;
- profit factor;
- turnover;
- exposure;
- trade count;
- average holding period;
- hit rate in top ranking buckets;
- precision/recall for binary labels where useful;
- Brier/log loss/calibration for probabilities;
- fill rate/unfilled rate;
- capacity/participation diagnostics;
- performance by year, regime, sector, liquidity decile.

## 10. Overfitting controls

- log all tried parameter sets in `experiment_registry`;
- predefine core grids;
- keep a final untouched OOS period where feasible;
- report Deflated/Probabilistic Sharpe or equivalent multiple-testing diagnostics where implemented;
- add Probability of Backtest Overfitting (PBO/CSCV) research diagnostic for strategies with many variants;
- bootstrap trade/return sequences for confidence intervals;
- require stability across folds, not one exceptional period.

The literature on backtest overfitting is a required engineering consideration, not optional polish.

## 11. Promotion gates

A strategy cannot become `production_enabled` based only on positive full-history return. Suggested gate:
- minimum OOS trade/sample count;
- positive net expectancy across majority of folds;
- acceptable drawdown;
- no single year/regime explains almost all profits;
- probability calibration acceptable if it emits probabilities;
- sensitivity to modest parameter changes is not catastrophic;
- execution/fill assumptions are supported by available data.

Thresholds are config, but reasons are stored.

## 12. Champion/challenger

Maintain:
- production champion version;
- challenger research versions;
- immutable comparison report.

Never silently replace champion because a newly tuned backtest looks better.

## 13. Backtest reproducibility

A run saves:
- git commit/hash;
- data snapshot/version range;
- strategy config hash;
- market rules/cost version;
- feature version;
- model/calibrator versions;
- random seeds;
- runtime package lock hash.

Running the same immutable setup should reproduce results within numerical tolerance.
