# DESIGN.md — Iran Market Radar UI/UX Design System & Standards

## 1. Visual Philosophy & Core Aesthetics
Iran Market Radar employs a professional, institutional-grade dark financial aesthetic tailored specifically for the Tehran Stock Exchange (TSE). The interface balances dense information hierarchy with calm clarity, eliminating visual noise while maintaining immediate readability for quant traders and portfolio managers.

---

## 2. Typography & Iranian Persian Localization
- **Primary Typeface:** **Vazirmatn (وزیرمتن)** — 100% Offline & Locally Hosted in `apps/web/public/fonts/`.
- **Weights Loaded:** 100 (Thin) to 900 (Black) + Variable WOFF2 font.
- **Direction:** Native Right-to-Left (`dir="rtl"`).
- **Digits & Numbers:** All numeric values, Rial/Toman prices, percentages, dates, and P/E multiples MUST be rendered in Persian digits using `toPersianDigits()`.

### BiDi Isolation Rule (Mandatory)
In Persian RTL text, mixing parentheses `()`, signs `+` / `-`, and percentage signs `٪` triggers browser BiDi reordering bugs. All formatted percentages and price brackets MUST use the unicode Left-to-Right Mark (`\u200E`):
- **Format:** `تارگت (\u200E+۵.۲٪\u200E)`
- **Output:** `تارگت (‎+۵.۲٪‎)` (Correct RTL alignment, sign never inverts).

---

## 3. Color Palette (Dark Theme / Terminal Slate)
| Token | Hex / HSL | Usage |
| :--- | :--- | :--- |
| **Canvas Background** | `#0a0e17` | Deep void background |
| **Card Surface** | `#111827` / `#161e2e` | Elevated panels and widgets with subtle border |
| **Card Border** | `#1f293d` | Structural separation |
| **Emerald (Profit / Bullish)** | `#10b981` | Gain %, buy signals, profit targets, smart money inflow |
| **Crimson (Loss / Bearish)** | `#ef4444` | Loss %, sell signals, stop-loss levels, smart money outflow |
| **Amber (Caution / Neutral)** | `#f59e0b` | Watchlist alerts, intermediate regimes, high volatility |
| **Cyan (Target / Info)** | `#06b6d4` | Entry zones, technical confluence, neutral regime |
| **Purple (Target 2 / ML)** | `#a855f7` | Extended targets, ML confidence badges |
| **Text Primary** | `#f9fafb` | Headings, symbol tickers, primary prices |
| **Text Secondary** | `#9ca3af` | Subtitles, parameter labels, timestamps |
| **Text Muted** | `#6b7280` | Micro-labels, table headers |

---

## 4. Financial Component Guidelines
1. **Interactive Candlestick Chart (`InteractiveStockChart.tsx`):**
   - SVG-based lightweight canvas rendering real OHLC bars.
   - Distinct overlaid horizontal levels for Entry (`cyan`), Target 1 (`emerald`), Target 2 (`purple`), and Stop Loss (`crimson`).
   - Volume sub-panel with real-buyer vs legal-buyer breakdown.
   - RSI oscillator sub-panel with 30/70 oversold/overbought thresholds.
2. **Opportunity Scanner Cards (`OpportunitiesView.tsx`):**
   - 4-column dense grid.
   - Immediate visibility of: Current Price, Entry Zone, Target (+%), Stop Loss (-%), Probability %, and Persian AI rationale.
3. **Institutional Tabular Data (`FundamentalView.tsx` & `HistoryView.tsx`):**
   - Compact row height (`py-2.5`), monospaced Persian digit alignment, colored delta pills.
4. **Drawdown Ladder & Risk Telemetry (`SettingsView.tsx`):**
   - Real-time latency tracking (p50/p95), completeness %, and emergency kill-switch trigger.

---

## 5. Pre-Flight Visual Verification Rules
Before approving any UI or component change:
1. Verify that no text falls back to Arial or Tahoma.
2. Verify that no price shows `۰ ریال` or missing values.
3. Verify that all prices match actual current Tehran Stock Exchange levels.
4. Verify that brackets around percentages do not invert.
5. Capture high-resolution headless Playwright screenshots across all 13 viewports.
