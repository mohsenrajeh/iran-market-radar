# Institutional Risk Policy — Iran Market Radar

## Policy Identification & Governance
- **Policy ID**: `POL-TSE-2026-V2.5`
- **Version**: `2.5.0-ENTERPRISE`
- **Effective Timestamp**: `2026-08-16T00:00:00Z`
- **Approved By**: Chief Risk Officer (CRO) & Quantitative Investment Committee
- **Status**: `ACTIVE`

---

## 1. Single Source of Truth
All frontend pages, API routes, Paper Trading Execution, Backtester, and Scorer query a single unified policy model (`packages.domain.risk_policy.ACTIVE_RISK_POLICY`).

---

## 2. Market Regime Parameter Matrix

| Parameter | RISK_ON | NEUTRAL | RISK_OFF | HALTED |
| :--- | :---: | :---: | :---: | :---: |
| **Max Gross Equity Exposure** | 70.0% NAV | 50.0% NAV | 25.0% NAV | 0.0% NAV |
| **Minimum Cash Reserve Floor** | 30.0% NAV | 50.0% NAV | 75.0% NAV | 100.0% NAV |
| **Risk Budget Per New Trade** | 0.35% NAV | 0.25% NAV | 0.15% NAV | 0.00% NAV |
| **Regime Upgrade Confirmation** | $\ge 2$ sessions | $\ge 2$ sessions | Immediate | Immediate |

---

## 3. Portfolio & Concentration Constraints

- **Max Active Positions**: $10$ positions.
- **Normal Max Position Weight**: $8.0\%$ NAV.
- **Exceptional Max Position Weight**: $10.0\%$ NAV (restricted to instruments with $ADTV_{20d} \ge 500\text{B}$ Rials).
- **Sector Exposure Cap**: $18.0\%$ NAV.
- **Max Positions Per Sector**: $3$ positions.
- **Correlated Cluster Cap**: $20.0\%$ NAV.
- **Correlation Haircut**: If rolling return correlation $> 0.70$, apply $0.50\times$ size multiplier.
- **Max Total Open Portfolio Risk**: $2.50\%$ NAV.
- **Max New Risk Added Per Day**: $0.80\%$ NAV.
- **Max New Notional Exposure Per Day**: $15.0\%$ NAV.
- **Max ADTV 20d Participation Rate**: $5.0\%$.

---

## 4. Drawdown Risk Ladder (from High Water Mark)

1. **Drawdown $\ge 4.0\%$**: Warning — Risk per new trade reduced to $0.75\times$.
2. **Drawdown $\ge 6.0\%$**: Moderate Risk — Risk per trade reduced to $0.50\times$, Max Gross Exposure capped at $35.0\%$.
3. **Drawdown $\ge 8.0\%$**: Defensive Mode — Freeze all new BUY orders, target exposure $\le 20.0\%$.
4. **Drawdown $\ge 12.0\%$**: **HARD KILL SWITCH** — Complete trading halt, cancels pending orders, requires manual review.

---

## 5. Daily Loss Circuit Breaker

- **Daily Loss $\ge 1.0\%$ NAV**: New trade risk reduced by $50\%$.
- **Daily Loss $\ge 1.5\%$ NAV**: Stop all new buy orders for remainder of session.
- **Daily Loss $\ge 2.0\%$ NAV**: Cancel all pending buy orders, activate Risk Reduction Mode.

---

## 6. Chase Prevention & Staged Scale-In

- **Max Planned Entry Chase Distance**: $+0.35R$. Any price above $+0.35R$ triggers `CHASE_BLOCKED`.
- **Staged Entry**:
  - **Stage 1 (40%)**: Initial entry upon passing all pre-trade risk gates.
  - **Stage 2 (35%)**: Only when trade advances to $CurrentR \ge +0.5R$ and remains $> -0.25R$. Stop moved to Breakeven ($+0.1R$).
  - **Stage 3 (25%)**: Only when regime is `RISK_ON` and $CurrentR \ge +1.0R$.
- **Averaging Down**: Strictly prohibited when trade is in loss.
