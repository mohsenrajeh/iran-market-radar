# Backtest Methodology & Statistical Validation — Iran Market Radar

## 1. Backtest Simulation Philosophy
The primary goal of backtesting is **institutional execution realism and out-of-sample reproducibility**, rather than curve-fitted parameter optimization.

---

## 2. Parameter Inputs

- **Strategy & Strategy Version**: Fully registered strategy class and version hash.
- **Universe Definition**: Point-in-Time historical membership eliminating survivorship bias.
- **Date Range**: Walk-forward partitioned (In-Sample vs Out-of-Sample).
- **Initial Capital**: Expressed in canonical integer Rials (e.g. $1,000,000,000$ Rials).
- **Execution & Queue Model**: Next-Bar Auction fill with volume participation cap and linear slippage.
- **Fee Version**: Versioned market fee schedule ($1.2562\%$ TSE equity).
- **Risk Policy**: Central Institutional Risk Policy (`POL-TSE-2026-V2.5`).

---

## 3. Comprehensive Output Metrics

- **Returns**: Net Total Return %, CAGR %.
- **Risk-Adjusted**: Sharpe Ratio, Sortino Ratio, Calmar Ratio.
- **Drawdowns**: Max Drawdown %, Average Drawdown %, Recovery Duration.
- **Trade Statistics**: Win Rate %, Profit Factor, Expectancy (Rials), Average R, Median R, MFE, MAE.
- **Frictional Costs**: Total Fees Paid (Rials), Total Slippage Cost (Rials), Portfolio Turnover.
- **Replay Verification**: Deterministic SHA-256 configuration hash for exact run reproduction.
