# Audit Trail & System Decisions — Iran Market Radar

## 1. System Version & Audit Record
- **System Version**: `2.5.0-ENTERPRISE`
- **Audit Date**: 2026-08-16
- **Auditor**: Senior Quant Architect & Trading Systems Team
- **Trading Mode**: `PAPER_TRADING_ONLY` (`LIVE_TRADING_ENABLED = false`)

---

## 2. Key Architectural Decisions & Resolved Defects

1. **Drawdown Kill-Switch Threshold**:
   - Standardized to **12.0%** across backend (`ACTIVE_RISK_POLICY`), ledger, UI banners, and health monitors.
2. **Double-Entry Accounting Invariant**:
   - Enforced: $\text{NAV} = \text{AvailableCash} + \text{ReservedCash} + \text{UnsettledCash} + \text{MarketValueOfPositions} - \text{Payables}$.
3. **Point-in-Time Discipline**:
   - All signal generation and backtesting strictly use `available_at` timestamps. Look-ahead bias blocked by Next-Bar ($t+1$) execution model.
4. **Chase Prevention Engine**:
   - Prevents chasing runaway prices when current market price exceeds $+0.35R$ of planned entry.
5. **Averaging Down Prohibition**:
   - Scaling in to a losing position ($CurrentR < 0$) is mathematically blocked by the risk engine.
6. **Unified Money & Reporting Model**:
   - Canonical integer Rials in backend logic (`MoneyIRR`); consistent Toman display ($1\text{ Toman} = 10\text{ Rials}$) in UI.
