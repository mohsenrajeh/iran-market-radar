# Architecture Decision Log

Codex must append dated decisions here when implementation details require assumptions.

Initial decisions:

- 2026-08-12 — Phase 1 is analysis + paper trading; live trading is fail-closed.
- 2026-08-12 — Official/authorized TSETMC/Codal access is preferred; no broker/API reverse engineering.
- 2026-08-12 — `p_profit`, `signal_strength`, `confidence`, and `opportunity_score` are distinct concepts.
- 2026-08-12 — Market rules and transaction costs are versioned/configurable, not permanent constants.
- 2026-08-12 — Tree-based ML ranker is preferred before deep-learning models because structured cross-sectional features and limited point-in-time datasets make it a stronger baseline.
- 2026-08-15 — Completed M0–M11 implementation: Monorepo packages (domain, market_rules, data_adapters, feature_engine, strategies S01-S09, ml calibrator), services (scorer, backtester, paper_broker, broker_gateway, collector), FastAPI REST API, and Next.js Persian RTL workstation dashboard.
- 2026-08-15 — Next-tradable bar execution (T+1) strictly enforced in both backtester and feature engine to eliminate lookahead bias.
- 2026-08-15 — Queue fill probability model implemented for TSE ±5% price limit conditions (صف خرید / صف فروش).
- 2026-08-15 — Institutional Persian typography with Vazirmatn and tabular numerals adopted for the user interface.
