# 07 — Signal Probability, Confidence and Opportunity Scoring

This is a critical design document. The UI must never pretend a composite score is a probability.

## 1. Four distinct outputs

### `p_profit` (0–1)
Calibrated estimate of:

`P(realized net return over horizon H > configured profit threshold | information available now)`

This is the only field that may be displayed as “احتمال سود”.

### `signal_strength` (0–100)
Cross-sectional percentile/rank of expected risk-adjusted edge among currently eligible instruments for the same horizon.

### `confidence` (0–100)
Reliability of the current estimate given OOS sample support, calibration quality, data quality, regime stability, model/strategy agreement and prediction uncertainty.

### `opportunity_score` (0–100)
Final ranking score balancing edge, probability, risk, executability and confidence. It is not a probability.

## 2. Label definition

For horizon `H`, default classification label:

```text
entry_time = next tradable executable point after signal timestamp
exit_time  = strategy-defined exit or fixed horizon for probability label
net_return = gross_return - fees - tax - modeled slippage
label = 1 if net_return > MIN_PROFIT_THRESHOLD_H else 0
```

For fixed-horizon ML calibration, use a consistent exit convention. Strategy-specific stop/target outcomes may have separate calibration tables.

## 3. Probability pipeline

1. Generate predictions only from time-aware validation/OOS windows.
2. Store raw predictor score/probability.
3. Fit calibrator on held-out predictions:
   - isotonic regression when sample size is sufficient;
   - Platt/logistic calibration for smaller/smoother samples;
   - compare with no-calibration baseline.
4. Evaluate:
   - Brier score;
   - log loss;
   - reliability curve;
   - expected calibration error;
   - bucket sample sizes.
5. Promote calibrator only if it improves reliability without unstable tails.

Never train the calibrator on in-sample fitted predictions.

## 4. Strategy probability

For deterministic strategies, estimate empirical `p_profit` by grouping historical OOS signals using signal-strength buckets, regime and horizon. Use hierarchical shrinkage:

```text
p_hat = (wins + prior_strength * global_rate) / (n + prior_strength)
```

The prior can be horizon/regime-aware. Do not show extreme probabilities from tiny samples.

## 5. ML probability

For the ML ranker, use model probability or a score-to-probability mapping only after time-aware calibration. Report OOS calibration metrics alongside the model version.

## 6. Ensemble probability

Do not simply average highly correlated strategy probabilities.

Recommended first implementation:
- build a meta logistic model on OOS base-strategy outputs + regime + liquidity features;
- regularize coefficients;
- train with walk-forward predictions only (stacking without leakage);
- calibrate meta-model again on a later held-out slice if enough history exists.

Fallback for low sample:
- reliability-weighted average with shrinkage and explicit correlation penalty.

## 7. Confidence formula

Initial interpretable implementation:

```text
confidence = 100 * clamp(
    0.25 * sample_support
  + 0.20 * calibration_quality
  + 0.20 * data_quality
  + 0.15 * model_agreement
  + 0.10 * regime_support
  + 0.10 * prediction_stability,
  0, 1)
```

Components are normalized 0–1. These are initial engineering weights, **not alpha weights**; keep configurable and later validate.

### Component examples
- `sample_support`: saturating function of OOS sample count for comparable signal bucket/regime.
- `calibration_quality`: inverse of normalized Brier/ECE with bucket coverage penalty.
- `data_quality`: source freshness/completeness score.
- `model_agreement`: agreement across genuinely distinct strategy families.
- `regime_support`: OOS sample/performance stability in current regime.
- `prediction_stability`: sensitivity of prediction to small feature/parameter perturbations.

Cap confidence when sample size is low regardless of attractive `p_profit`.

## 8. Signal strength

For each horizon:

```text
edge = expected_return_net / max(expected_adverse_excursion, volatility_floor)
signal_strength = percentile_rank(edge among eligible universe) * 100
```

If no expected-return model exists, use a standardized strategy-ensemble raw edge transformed to current cross-sectional percentile.

## 9. Opportunity score

Initial transparent formula:

```text
edge_component         = percentile(expected_net_edge)
probability_component  = clamp((p_profit - base_rate) / (1 - base_rate), 0, 1)
risk_component         = 1 - normalized_risk_penalty
execution_component    = liquidity_score * fill_probability_score

opportunity_score = 100 * (
    0.30 * edge_component
  + 0.25 * probability_component
  + 0.15 * confidence/100
  + 0.15 * execution_component
  + 0.10 * regime_fit
  + 0.05 * fundamental_event_support
) * risk_component
```

Use this only as a v1 ranking bootstrap. Save component values. Later replace weights with a constrained model trained exclusively on OOS data if it materially improves ranking stability.

## 10. Grades

Suggested defaults, configurable:
- A+: score >= 90, confidence >= 75, p_profit above required threshold, no blocking risk flag;
- A: >= 80;
- B: >= 70;
- C/watchlist: >= 60;
- below: not published as actionable.

Do not guarantee a number of A signals.

## 11. Entry zone

The strategy owns entry logic. Generic helpers:
- breakout: `[breakout_level, breakout_level + k*ATR]` capped by executability;
- pullback: structural support ± ATR band;
- momentum: next-tradable price with maximum chase distance;
- event: opening/next liquid execution with slippage guard.

If price is locked at upper limit with low fill likelihood, signal can be high-quality but `actionable=false`.

## 12. Stop / invalidation

Prefer thesis invalidation + volatility buffer over arbitrary fixed percentages:
- below breakout/retest structure;
- below swing low;
- ATR multiple;
- loss of sector/flow condition;
- new negative material filing.

Store `hard_price_stop` separately from `logical_invalidation` when applicable.

## 13. Targets / exit

Support:
- fixed R multiples (e.g. 1.5R/2R) for display/testing;
- trailing ATR/structure stop;
- time stop at horizon;
- signal decay / opposite signal;
- event exit.

Backtest each exit policy independently; do not cherry-pick per historical trade.

## 14. UI example

```text
فملی
Opportunity Score: 86/100
احتمال سود 5روزه پس از هزینه: 67%
Confidence: 78/100
Signal Strength: 92nd percentile
Entry: 7,850–7,930
Invalidation: 7,560 (شکست ساختار + 1 ATR)
Top reasons:
  + Relative strength top 8%
  + Sector rotation positive
  + Volume 2.2x robust median
  + Real-money flow positive 3 sessions
Risk:
  - Near upper allowed range / fill risk medium
```

The exact numbers must come from real computation, never demo constants in production.
