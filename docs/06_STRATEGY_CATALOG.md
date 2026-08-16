# 06 — Strategy Catalog

No strategy is “best” before Iranian-market out-of-sample validation. Build a diversified registry of hypotheses and let the validation/scoring layer determine which survive. The core portfolio is long-only by default because execution/shorting availability is market-specific.

## Strategy interface

Each strategy implements roughly:

```python
class Strategy(Protocol):
    key: str
    version: str
    required_features: set[str]
    supported_horizons: set[str]

    def eligibility(self, context) -> EligibilityResult: ...
    def generate(self, context) -> list[StrategyCandidate]: ...
```

Candidate includes raw signal, entry model, invalidation, exit model, reason codes and feature evidence.

---

## S01 — Cross-Sectional Momentum / Relative Strength

### Hypothesis
Recent winners and stronger stocks/sectors may continue to outperform over intermediate horizons.

### Candidate logic
- rank adjusted returns over 20/60/120-session windows;
- rank residual return vs sector/market;
- require acceptable liquidity;
- optionally skip the most recent few sessions in medium-term momentum variants to test short-term reversal effects;
- favor aligned sector momentum.

### Entry
Current/next tradable price or controlled pullback; not blindly at price-limit queue.

### Invalidation
Loss of relative strength + structure/volatility stop.

### Validation
Test multiple *predefined* lookbacks, not hundreds of mined combinations.

Evidence base: Jegadeesh & Titman momentum research; must validate locally.

---

## S02 — Time-Series Trend

### Hypothesis
A symbol's own trend persists in some horizons.

Features:
- regression slope/R²;
- EMA trend stack;
- volatility-normalized momentum;
- market/sector alignment.

Avoid entering mature parabolic moves with severe liquidity/queue risk.

---

## S03 — Breakout + Volatility/Volume Expansion

### Hypothesis
Breakout from a defined range with genuine participation may continue.

Requirements:
- close/last breaks a prior rolling high or compression range;
- volume/value traded exceeds robust baseline;
- spread/liquidity acceptable;
- sector/market not strongly contradictory;
- penalize upper-limit locked names where fill probability is poor.

Entry zone may be breakout confirmation or retest depending tested variant.

---

## S04 — Trend Pullback / Continuation

### Hypothesis
Strong trends can offer better risk/reward after controlled retracement.

Requirements:
- established trend/relative strength;
- pullback of configurable ATR/percent/structure depth;
- declining sell pressure or improving order/client flow;
- no fundamental negative event.

Invalidation below structural swing/ATR band.

---

## S05 — Short-Term Mean Reversion (Selective)

### Hypothesis
Extreme short-term moves can partially revert, especially when long-term quality/trend remains intact.

Do **not** buy every oversold RSI.

Requirements might include:
- extreme 1–5d residual return;
- long-term trend/quality filter;
- liquidity;
- no fresh adverse disclosure;
- evidence of sell-pressure exhaustion / flow reversal.

This is high-risk around lower price-limit queues; execution model is critical.

---

## S06 — Volume / Turnover Anomaly

### Hypothesis
Abnormal participation can precede or confirm repricing.

Features:
- robust volume z-score;
- value traded percentile;
- turnover acceleration;
- price-volume confirmation/divergence;
- trade count/per-capita measures where available.

Use as both independent candidate generator and ensemble confirmation.

---

## S07 — حقیقی/حقوقی Flow Accumulation

Iran-specific hypothesis using published client-type data.

Potential positive setup:
- persistent net real inflow;
- real buy per-capita materially above sell per-capita;
- accumulation while price holds/recovers;
- sector-relative confirmation;
- sufficient participant counts and liquidity.

Negative/distribution setup acts as penalty/exit evidence.

Do not use a single day's huge ratio without sample/denominator controls.

---

## S08 — Order-Book / Queue Pressure (Experimental)

Only enable after collecting enough high-quality authorized snapshots.

Features:
- depth imbalance;
- spread;
- queue growth/decay;
- repeated replenishment;
- distance to price limit;
- historical fill probability of similar queue states.

This may provide execution timing more than medium-horizon alpha.

---

## S09 — Sector Rotation

### Hypothesis
Capital leadership rotates across Iranian sectors; selecting strong sectors first may improve stock selection.

Rank sectors on:
- relative returns;
- breadth;
- turnover/flow acceleration;
- dispersion;
- fundamental/event backdrop.

Then rank top stocks inside top sectors by RS/liquidity/flow.

---

## S10 — Fundamental Quality + Value

Longer horizon (10–20d+ and watchlist generation):
- quality/profitability;
- reasonable leverage;
- sector-relative valuation;
- positive earnings/sales quality;
- liquidity.

Avoid simplistic “lowest P/E wins”. Use sector/negative-denominator handling.

---

## S11 — Fundamental Momentum / Monthly Sales Surprise

Particularly relevant for companies with useful monthly operating reports.

- YoY growth;
- seasonality-adjusted MoM;
- 3m/6m acceleration;
- surprise vs historical distribution;
- margin/price/volume decomposition if source supports it;
- published-at timestamp gating.

Signal can combine with price confirmation.

---

## S12 — Codal Event-Driven

Candidate classes:
- material positive/negative disclosures;
- significant contracts;
- production/sales changes;
- capital increases;
- dividend/AGM outcomes;
- clarification/correction risk.

Use structured event rules first; NLP only adds classification/summarization confidence.

---

## S13 — ML Cross-Sectional Ranker

### Purpose
Predict relative/absolute future return or probability of positive net return from a broad tabular feature set.

### Initial model ladder
1. regularized logistic/linear baseline;
2. Random Forest / Extra Trees diagnostic;
3. gradient-boosted trees (LightGBM/XGBoost/CatBoost) as primary nonlinear candidate;
4. neural network only after tree models and data discipline are mature.

Research in empirical asset pricing has found tree and neural-network methods useful for nonlinear interactions, but this is not a guarantee in Iran. Local walk-forward evidence decides promotion.

### Labels
For each horizon H:
- future executable return after estimated round-trip costs;
- binary label `return_net > threshold` for probability model;
- optional cross-sectional rank target.

Use next-tradable execution assumptions.

### Training
- rolling training window;
- validation window;
- forward OOS window;
- no random split;
- feature transforms fit only on training window;
- calibration on held-out predictions.

---

## S14 — Regime-Gated Ensemble

This is the final meta-strategy, not a raw predictor.

- maintain performance/reliability of each strategy by regime and horizon;
- down-weight strategies that historically fail in current regime;
- require independent evidence rather than counting duplicate indicators as separate votes;
- use shrinkage toward equal/neutral weights when OOS sample is small.

---

## S15 — Bubble/Fragility Risk Diagnostic (Research)

Optional research module may test LPPLS or simpler acceleration/fragility diagnostics for broad market/sector risk. Use as a **risk penalty**, not an automatic short signal.

---

## “Private/proprietary” strategy support

No one can honestly provide secret profitable algorithms without validation. Instead, create a `proprietary/` strategy plugin boundary so future private hypotheses can be added without touching the engine:

```text
packages/strategies/core/          # public/explainable
packages/strategies/experimental/  # research
packages/strategies/proprietary/   # user-owned private strategies, gitignored or private repo
```

All proprietary strategies must still obey the exact same timestamp, backtest, calibration and audit standards.
