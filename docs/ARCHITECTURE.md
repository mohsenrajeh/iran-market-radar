# Architecture & System Design — Iran Market Radar

## Overview & Mission
Iran Market Radar is an enterprise-grade quantitative scanning, valuation, and simulated paper-trading engine designed for the Tehran Stock Exchange (TSE) and Iran Fara Bourse (IFB).
Phase 1 operates in **Paper Trading Only** (`LIVE_TRADING_ENABLED = false`), governed by an institutional risk engine and double-entry accounting ledger.

---

## 1. System Layers & Data Flow

```
[ TSETMC Web Service / REST API ]   [ Codal / SEDRA Official Disclosures ]
                    │                                    │
                    ▼                                    ▼
       ┌────────────────────────┐           ┌────────────────────────┐
       │   TSETMC DataAdapter   │           │   Codal DataAdapter    │
       └───────────┬────────────┘           └────────────┬───────────┘
                   │                                     │
                   └──────────────────┬──────────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │   IngestionCoordinator    │
                        │ (Point-in-Time Discipline)│
                        └─────────────┬─────────────┘
                                      ▼
     ┌─────────────────────────────────────────────────────────────────┐
     │                       Canonical Domain Models                   │
     │   (Instrument, EODBar, ClientTypeSnapshot, Filing, CashLedger)  │
     └────────────────────────────────┬────────────────────────────────┘
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
 ┌───────────────────────────┐                 ┌───────────────────────────┐
 │       FeatureEngine       │                 │     FundamentalEngine     │
 │ (20+ Technical Indicators)│                 │ (Piotroski F-Score / TTM) │
 └─────────────┬─────────────┘                 └─────────────┬─────────────┘
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      ▼
                         ┌─────────────────────────┐
                         │    Strategy Registry    │
                         │(12 Independent Strategy)│
                         └────────────┬────────────┘
                                      ▼
                         ┌─────────────────────────┐
                         │   EnsembleScorer & ML   │
                         │ (Isotonic Calibration)  │
                         └────────────┬────────────┘
                                      ▼
                         ┌─────────────────────────┐
                         │  PreTrade Risk Ticket   │
                         │ (Multi-Constraint Size) │
                         └────────────┬────────────┘
                                      │
         ┌────────────────────────────┴────────────────────────────┐
         ▼                                                         ▼
┌─────────────────────────────┐                         ┌─────────────────────────────┐
│    Paper Broker Service     │                         │   Backtest Simulation       │
│  (Next-Bar Order Execution) │                         │  (Walk-Forward Simulation)  │
└──────────────┬──────────────┘                         └──────────────┬──────────────┘
               ▼                                                       ▼
┌─────────────────────────────┐                         ┌─────────────────────────────┐
│ Double-Entry Cash Ledger    │                         │ Performance Analytics &     │
│ (NAV Invariant Reconciler)  │                         │ Exact Replay Hashes         │
└─────────────────────────────┘                         └─────────────────────────────┘
```

---

## 2. Mandatory Architectural Boundaries

- **`DataAdapter` Layer**: Transport, rate limiting, and deserialization only. Never makes trading decisions.
- **`Canonical Market Data`**: Clean entities (`Instrument`, `EODBar`, `ClientTypeSnapshot`, `Filing`) with explicit Point-in-Time metadata (`available_at`, `ingested_at`).
- **`FeatureEngine`**: Deterministic feature computation (SMA, EMA, Ichimoku, ADX, Supertrend, Stochastic RSI, MFI, OBV, CMF, Keltner/Donchian channels).
- **`StrategyRegistry`**: 12 independent quantitative strategies outputting votes in $[0, 1]$.
- **`SignalCalibrator`**: Converts composite factor rankings into calibrated empirical probabilities ($p_{\text{profit}}$) via Isotonic Regression, evaluated using Brier Score and ECE.
- **`RiskPolicy` & `PositionSizingSolver`**: Single Source of Truth for risk budgets, sector caps, correlation cluster limits, and staged scale-in plans.
- **`ExecutionSimulator`**: Core execution module shared between Paper Broker and Backtester ensuring Next-Bar ($t+1$) execution with price limit and queue modeling.
- **`AccountingReconciler`**: Double-entry ledger enforcing $NAV = \text{Cash} + \text{Positions} + \text{Receivables} - \text{Payables}$.

---

## 3. Technology Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, NumPy, SciPy.
- **Queue & Storage**: PostgreSQL 16 (TimescaleDB ready), Redis.
- **Frontend**: Next.js 14 (React, TypeScript), Persian RTL, TailwindCSS, CSS Variables.
- **Testing**: Pytest, Property/Invariant Tests, Regression Tests.
