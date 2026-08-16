# CHECKLIST.md — Mandatory Quality Gates & Pre-Flight Verification

Every AI Agent and Developer MUST execute and verify all items in this checklist before marking any task as complete or approved.

---

## 1. Data Integrity & Financial Realism Gate
- [ ] **Price Sanity:** Confirm all stock prices match authentic, current Tehran Stock Exchange prices (e.g. Shabriz ~43,240 Rials, Foulad ~2,785 Rials, Webmellat ~1,291 Rials).
- [ ] **No Zero Values:** Verify that no card, signal, target, or stop loss renders as `۰ ریال` or `NaN`.
- [ ] **Point-In-Time Invariant:** Ensure indicators and features computed at timestamp T only access data available on or before T.
- [ ] **R/R Invariant:** Ensure every published opportunity satisfies minimum Risk/Reward ratio (≥ 1.8) and daily limit constraints (±5%).

---

## 2. Typography & Iranian RTL Localization Gate
- [ ] **Local Offline Fonts:** Confirm all 10 Vazirmatn font files (`WOFF2`) load strictly from `/fonts/` with zero Google Fonts network requests.
- [ ] **Persian Digit Conversion:** Confirm all numbers, percentages, dates, and prices pass through `toPersianDigits()`, `formatPercentFa()`, or `formatRial()`.
- [ ] **BiDi Isolation:** Confirm all percentages with parentheses render without inversions using `\u200E` (e.g. `(‎+۵.۲٪‎)`).
- [ ] **Persian Copy:** Confirm all user-facing rationale strings, strategy names, table headers, and error messages are written in accurate, institutional Persian.

---

## 3. Architecture & Code Cleanliness Gate
- [ ] **Strict Monorepo Separation:** Data adapters -> Canonical domain -> Feature engine -> Strategies -> Calibrator -> Scorer -> Risk -> Broker.
- [ ] **No Hardcoded Secrets:** Verify no private keys, passwords, or broker credentials exist in source code.
- [ ] **Container Parity:** Verify backend runs cleanly on port `8742` and web frontend on port `3742` without port collision.

---

## 4. Visual Verification Gate (Playwright Headless)
- [ ] Run `node scripts/capture_all_views.js` to render and photograph all 13 application views:
  1. Main 360 Dashboard (`OverviewView`)
  2. Quantitative Opportunity Scanner (`OpportunitiesView`)
  3. 360 Symbol Modal - Chart & Signals (`InteractiveStockChart`)
  4. 360 Symbol Modal - TSETMC & Codal Tabs
  5. Open Positions & 1 Billion Toman Paper Portfolio (`PaperBrokerView`)
  6. Closed Trades Ledger & Accounting (`HistoryView`)
  7. Trade Autopsy & Execution Drawer
  8. Fundamental Valuation & Piotroski F-Score Matrix (`FundamentalView`)
  9. Live Codal Filings Stream
  10. Trading Lab & Strategy Health (`TradingLabView`)
  11. Structured Post-Trade Lessons
  12. Research Queue & Champion vs Challenger
  13. Data Health, Risk Policies & Exchange Fee Breakdown (`SettingsView`)
- [ ] Inspect generated screenshots in `screenshots/` to ensure zero rendering glitches.
