# Iran Market Radar (رادار هوشمند بازار سرمایه ایران)

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.1-black.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Institutional-grade algorithmic market scanner, quantitative research lab, and automated paper trading workstation tailored specifically for the Tehran Stock Exchange (TSE / IFB).

---

## 🌟 Key Capabilities

1. **12 Quantitative Trading Strategies (`packages/strategies/`):**
   - Momentum & Trend-Following (EMA Multi-Ribbon + Breakout)
   - Mean Reversion (RSI 14 + Lower Bollinger Band bounce)
   - Smart Money Flow (Real vs Legal Buyer Power Ratio + Net Inflow)
   - 20-Day Range Breakout + Volume Z-Score Anomaly
   - Fundamental Growth & Value (P/E & P/S discount + Codal quarterly growth)
   - Sector Rotation & Relative Strength
   - Multi-Timeframe Trend Confirmation
   - Ichimoku Cloud Kumo Breakout (Tenkan/Kijun cross above cloud)
   - Volatility Squeeze (Bollinger inside Keltner Channels)
   - BBSqueeze Explosion Breakout
   - Multi-Indicator Confluence (5 of 8 bullish agreement)
   - Smart Money Divergence (Price decline vs smart money accumulation)

2. **Accurate Iranian Market Data & Point-in-Time Discipline:**
   - Real-world TSE prices (e.g., Shabriz 43,240 Rials, Foulad 2,785 Rials, Webmellat 1,291 Rials).
   - Real-time Codal announcement classification (Positive disclosure, revenue surge).
   - TSETMC microstructure: Orderbook top 5 levels, buy/sell per-capita power, daily ±5% limits.
   - Exact 1.2562% round-trip exchange fees and tax deduction calculations.

3. **100% Offline Persian RTL Typography & Design System:**
   - Built with local **Vazirmatn (وزیرمتن)** fonts (WOFF2) with zero external Google Fonts network dependencies.
   - Unicode Left-to-Right Mark (`\u200E`) isolation to prevent inverted parentheses and percentages in Persian RTL.
   - Professional institutional slate dark theme with SVG candlestick charts, overlay targets, stop loss levels, and client power meters.

4. **13 Complete Workstation Views:**
   - Main 360 Market Dashboard
   - Quantitative Opportunity Scanner (4-column grid with entry/target/stop-loss)
   - 360 Symbol Modal (Interactive SVG Candlestick Chart, Indicators, Orderbook, Codal)
   - Open Positions & 1 Billion Toman Portfolio Workstation
   - Closed Trades Ledger & Accounting (Double-entry reconciliation)
   - Trade Autopsy & Multi-Factor Drawer
   - Fundamental Valuation & Piotroski F-Score Matrix
   - Real-Time Codal Announcements Feed
   - Trading Lab & Strategy Health Matrix (Mathematical Expectancy `+0.42R`, Win Rate, Calibrated Probabilities)
   - Structured Post-Trade Lessons & Rule Extraction
   - Research Queue (Champion vs Challenger Strategy Evaluation)
   - Data Pipeline Health, Risk Policies & Fee Breakdown

---

## 🚀 Quick Start with Docker

```bash
# 1. Clone repository
git clone https://github.com/mohsenrajeh/iran-market-radar.git
cd iran-market-radar

# 2. Copy environment template
cp .env.example .env

# 3. Bootstrap all services with Docker Compose
docker compose up -d --build
```

### 🌐 Access Endpoints
- **Web Application (Persian RTL):** [http://127.0.0.1:3742](http://127.0.0.1:3742)
- **REST API & Swagger Docs:** [http://127.0.0.1:8742/docs](http://127.0.0.1:8742/docs)
- **PostgreSQL Database:** `127.0.0.1:5742`
- **Redis Cache:** `127.0.0.1:6742`

---

## 🏗 Repository Architecture

```text
apps/
  api/                     # FastAPI backend (ports: 8742)
  web/                     # Next.js 14 frontend (ports: 3742)
services/
  collector/               # Market data synchronization & radar scanning
  paper_broker/            # Automated paper trading & hourly auto-trader
  scorer/                  # Signal aggregation & probability calibration
packages/
  domain/                  # SQLAlchemy 2.0 models & Pydantic v2 schemas
  feature_engine/          # 20+ technical indicators & regime classifiers
  strategies/              # 12 quantitative trading strategy implementations
  market_rules/            # TSE fees, price limits, tick sizes
  data_adapters/           # TSETMC, Sahamyab, Codal, and Fixture adapters
  ml/                      # Isotonic calibration & ensemble scoring
  shared/                  # Config, logging, database session management
screenshots/               # 13 high-resolution visual verification captures
```

---

## 📋 Quality Gates & Verification

Before approving code, ensure all pre-flight checks pass:
```bash
# Run backend unit tests
pytest tests/ -v

# Capture and verify all 13 viewports visually
node scripts/capture_all_views.js
```

See [CHECKLIST.md](CHECKLIST.md) and [DESIGN.md](DESIGN.md) for full engineering and design standards.

---

## ⚖️ License
MIT License. Built for research and quantitative paper trading.
