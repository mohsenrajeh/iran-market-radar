# AGENTS.md — Iran Market Radar Core Operational Specification

## 1. Mission & System Overview
Build a robust, auditable, institutional-grade Iranian market opportunity scanner, quant research lab, and paper trading workstation. Phase 1 is analysis + paper trading only. Design the code so an authorized broker can later be connected through `BrokerAdapter` without modifying data, strategy, scoring, or risk layers.

---

## 2. Core Operating Principles
1. **Correctness over speed:** Look-ahead bias, financial leakage, stale data, and unrealistic price fills are release-blocking defects.
2. **Authentic Market Data:** Stock prices, volumes, client type flows (حقیقی/حقوقی), and financial ratios must reflect real Tehran Stock Exchange figures.
3. **Deterministic & Explainable:** Every signal emitted by the 12 strategies must provide machine-readable components and an institutional-grade Persian explanation.
4. **Configurable Market Rules:** Trading hours (09:00 - 12:30), ±5% daily price limit, 1.2562% round-trip exchange fees and taxes are centrally configured in `packages/market_rules/`.
5. **No Live Broker Automation without Explicit Gate:** Live execution requires all five safety flags:
   ```text
   TRADING_MODE=live
   LIVE_TRADING_ENABLED=true
   BROKER_ADAPTER=<authorized implementation>
   BROKER_CREDENTIALS present
   RISK_KILL_SWITCH_ARMED=true
   ```

---

## 3. Quantitative Strategy Catalog (12 Core Engines)
1. `s01_momentum.py` — Momentum & Trend-Following (EMA 10/20/50 alignment + Breakout volume)
2. `s02_mean_reversion.py` — Mean Reversion (RSI < 30 + Bollinger Band Lower bounce)
3. `s03_smart_money.py` — Smart Money Flow (حقیقی / حقوقی buy-power ratio > 1.4 + Net inflow)
4. `s04_breakout.py` — 20-Day Range Breakout + Volume Spike (Z-Score > 2.0)
5. `s05_fundamental_growth.py` — Fundamental Growth & Value (P/E discount + Codal revenue growth > 30%)
6. `s06_sector_rotation.py` — Sector Relative Strength (Leading market sectors)
7. `s07_multi_timeframe.py` — Multi-Timeframe Trend Confirmation (Weekly + Daily alignment)
8. `s08_ichimoku.py` — Ichimoku Kumo Breakout (Price above cloud + Tenkan/Kijun cross)
9. `s09_volatility_squeeze.py` — Bollinger Bands Inside Keltner Channel squeeze
10. `s10_bb_squeeze.py` — Volatility Explosion Breakout
11. `s11_confluence.py` — Multi-Indicator Confluence (5 of 8 bullish indicators agreement)
12. `s12_smart_money_divergence.py` — Price drop divergence against smart money accumulation

---

## 4. Mandatory Pre-Flight Verification Gate
Before closing any task or approving code changes, the agent MUST:
1. Verify unit tests pass with `pytest tests/`.
2. Verify all 10 Vazirmatn fonts load locally from `apps/web/public/fonts/`.
3. Verify numeric formats adhere to Persian BiDi rules with `\u200E` mark.
4. Verify stock prices match actual current Tehran Stock Exchange levels.
5. Capture and inspect Playwright visual screenshots (`node scripts/capture_all_views.js`).
