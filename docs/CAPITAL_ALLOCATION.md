# Capital Allocation & Mathematical Position Sizing — Iran Market Radar

## 1. Strategy Family Allocations

The investable capital (Gross Equity Exposure) is bucketed into 3 distinct quantitative families:

- **Fundamental + Long-Term Trend**: $50.0\%$
- **Technical Swing & Momentum**: $30.0\%$
- **Codal Disclosures & Event-Driven**: $20.0\%$

> [!IMPORTANT]
> Unused strategy family allocations are **NOT** redistributed to other buckets. Unused capacity remains strictly in Cash to prevent style drift and forced risk-taking.

---

## 2. Strategy Promotion Tiers

- **Champion Tier**: $\le 85.0\%$ of family allocation.
- **Diversifier Tier**: $\le 10.0\%$ of family allocation.
- **Challenger Tier**: $\le 5.0\%$ of family allocation.

Promotion from Challenger to Champion requires independent Out-Of-Sample (OOS) validation and walk-forward verification.

---

## 3. Position Sizing Mathematical Optimization Formula

### Step 1: Compute Risk Budget
$$\text{RiskBudget} = \text{NAV} \times \text{RiskPerTrade}_{\text{Regime}}$$

### Step 2: Compute Effective Total Loss Percentage
$$\text{EffectiveLossPct} = \frac{\text{PlannedEntry} - \text{StopPrice}}{\text{PlannedEntry}} + \text{Fees}_{\text{RoundTrip}} + \text{Slippage} + \text{GapBuffer} + \text{QueueBuffer}$$

### Step 3: Compute Unconstrained Risk-Based Position
$$\text{RiskBasedPosition} = \frac{\text{RiskBudget}}{\text{EffectiveLossPct}}$$

### Step 4: Multi-Constraint Boundary Solver
$$\text{FinalPosition} = \min \begin{pmatrix}
\text{RiskBasedPosition} \times \text{CorrelationHaircut}, \\
\text{SymbolCap} \ (8\% \text{ or } 10\% \text{ NAV}), \\
\text{SectorRemainingCapacity} \ (18\% \text{ NAV} - \text{CurrentSectorExposure}), \\
\text{CorrelationClusterCapacity} \ (20\% \text{ NAV}), \\
\text{LiquidityCapacity} \ (5\% \text{ of } ADTV_{20d}), \\
\text{AvailableCash} \ (\text{Cash} - \text{CashFloor}), \\
\text{DailyNewExposureCapacity} \ (15\% \text{ NAV} - \text{TodayNewExposure}), \\
\text{PortfolioExposureCapacity} \ (\text{RegimeCap} - \text{CurrentGrossExposure})
\end{pmatrix}$$

$$\text{FinalQuantity} = \left\lfloor \frac{\text{FinalPosition}}{\text{CurrentPrice}} \right\rfloor$$
