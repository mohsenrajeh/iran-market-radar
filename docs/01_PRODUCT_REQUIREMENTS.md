# 01 — Product Requirements

## 1. Product goal

Build an always-on system that scans the Iranian equity market and reduces hundreds of instruments to a small, explainable, ranked list of actionable opportunities. The system is a decision-support and research platform first; automation of order execution is a later layer.

## 2. Primary users

### Owner / Trader
Needs a fast list of the strongest opportunities, why they are strong, entry/exit levels, probability estimates and risks.

### Research/Admin
Needs strategy configuration, backtests, model/calibration diagnostics, data-health controls, experiment history and system settings.

## 3. Core user stories

1. As a trader, I can open the dashboard and immediately see the current market regime and top opportunities.
2. I can sort/filter by opportunity score, probability of profit, strategy, horizon, sector, liquidity, market and risk flags.
3. I can open a symbol and see price/volume, sector-relative strength, client-type flow, order-book/queue state, filings/events, feature values and strategy votes.
4. I can see an entry zone, invalidation/stop logic and exit logic generated from the strategy and market structure.
5. I can distinguish `p_profit` from a generic score.
6. I can inspect the historical OOS performance of the exact strategy/model version that generated the signal.
7. I can launch a reproducible backtest with an immutable configuration snapshot.
8. I can approve a signal into paper trading and later compare expected vs realized execution.
9. I can see if data is stale or a source is degraded before trusting signals.
10. I can disable any strategy globally or by regime/market/instrument class.

## 4. Supported analysis horizons

Default horizons:
- intraday / same-session: experimental, only when data quality and executable snapshots are sufficient;
- 1 trading day;
- 3 trading days;
- 5 trading days;
- 10 trading days;
- 20 trading days.

The ranking page defaults to 3d/5d swing opportunities until enough intraday history exists.

## 5. Market universe

Collector stores all instrument metadata made available by the authorized source. Strategy eligibility is explicit:

### Default enabled
- ordinary listed shares on TSE;
- ordinary listed shares on IFB;
- equity rights where the strategy explicitly supports their different mechanics;
- equity ETFs where compatible.

### Default disabled in equity strategies
- fixed-income instruments;
- options/futures;
- commodity/energy instruments;
- instruments with insufficient history;
- suspended/non-tradable instruments;
- extremely illiquid securities;
- instruments under configured supervision/risk exclusions.

Separate strategies can later support each disabled class.

## 6. Opportunity output

Every opportunity must contain:
- canonical instrument identity (ISIN/instrument code/symbol/name);
- market and sector;
- timestamp and data freshness;
- horizon;
- direction (`long` in v1);
- `p_profit_after_costs`;
- `confidence`;
- `signal_strength`;
- `opportunity_score`;
- expected return distribution (mean/median and quantiles where model supports it);
- expected adverse excursion / drawdown estimate;
- entry zone;
- invalidation/stop logic;
- exit/target/trailing logic;
- liquidity and executability scores;
- strategy votes and contribution breakdown;
- regime label;
- top Persian reasons;
- risk flags;
- related recent filings/events;
- backtest/OOS summary for exact model/strategy version.

## 7. Ranking behavior

- Do not force a minimum number of opportunities.
- If no instrument exceeds eligibility and edge thresholds, show “فرصت با کیفیت کافی پیدا نشد”.
- Rank only executable candidates.
- A signal can be “interesting” but not “actionable” if queue/liquidity/uncertainty is poor.
- Provide independent lists for horizons rather than mixing all horizons into one score.

## 8. Signal lifecycle

`candidate -> validated -> ranked -> published -> expired/invalidated -> outcome_recorded`

Optional paper-trading lifecycle:

`published -> approved -> pending_entry -> filled/unfilled -> open -> exit_pending -> closed`

Every transition is auditable.

## 9. Market regime

At minimum classify:
- broad risk-on / bullish;
- neutral/range;
- risk-off / bearish;
- high-volatility / shock;
- illiquidity/closure/degraded market conditions.

Regime must be derived from market/index breadth, cross-sectional returns, volatility, turnover and liquidity; it is not a hand-entered label only.

## 10. Notifications (optional in v1, interface required)

Allow Telegram/web-push/email adapters later. Alert only on:
- newly published A-grade opportunities;
- material score/probability change;
- invalidation/exit event for followed/paper positions;
- data-source degradation;
- risk kill-switch event.

Do not spam repeated unchanged signals.

## 11. Performance expectations

For a typical Iran equity universe:
- EOD feature rebuild should complete in minutes, not hours.
- Intraday update should process new snapshots incrementally.
- API opportunity query p95 target < 500 ms from cached/precomputed results.
- UI should never compute portfolio-grade analytics in the browser.

## 12. Trust requirements

The UI must surface:
- “آخرین بروزرسانی داده”;
- data quality badge;
- model/strategy version;
- OOS sample size;
- probability calibration status;
- an explicit note when an estimate is experimental or low-sample.

## 13. Success metrics for the software

Engineering/product success is not measured by raw profit alone. Track:
- ingestion completeness/freshness;
- reproducible backtests;
- calibration error/Brier score;
- precision of top-ranked bucket vs lower buckets;
- realized vs simulated fill rate;
- strategy stability across OOS windows;
- max drawdown and turnover;
- percentage of signals with complete explanation and no stale data.
