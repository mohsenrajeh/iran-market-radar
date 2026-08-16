# Machine Learning Calibration & Statistical Validation — Iran Market Radar

## 1. Distinction Between Score & Probability
- **Composite Score ($0 \dots 100$)**: Multi-factor ordinal ranking indicating relative opportunity strength.
- **Calibrated Probability ($p_{\text{profit}} \in [0, 1]$)**: Calibrated posterior probability derived from Isotonic Regression.

---

## 2. Active Model Version & Calibration Metrics
- **Champion Model**: `v2.4.0-ISOTONIC-LOCKED`
- **Label Definition (`LABEL_CONTRACT_v1`)**: Net realized return $> +0.0\%$ after deducting $1.2562\%$ fees and $20\text{ bps}$ slippage within $5$ trading sessions.
- **Brier Score**: $0.142$
- **Expected Calibration Error (ECE)**: $0.048$
- **Log Loss**: $0.468$
- **95% Wilson Confidence Interval**: Computed on all reliability bins.

---

## 3. Production Champion / Challenger Workflow
Production decision weights remain frozen and immune to online overfitting from small sample trade counts ($n=6$). Any proposed parameter adaptation must pass offline walk-forward backtesting, out-of-sample validation, and risk committee approval.
