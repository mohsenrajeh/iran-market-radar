# START HERE

Give this entire folder to Codex.

Tell Codex:

> Read `AGENTS.md`, then `codex/CODEX_MASTER_PROMPT.md`, then all files under `docs/`, `config/`, and `schemas/`. Build the project in the milestone order from `docs/15_IMPLEMENTATION_ROADMAP.md`. Phase 1 must be fully functional analysis + backtesting + paper trading and must not submit real broker orders. Do not invent undocumented TSETMC/broker endpoints; inspect current official documentation and implement authorized adapters. Keep a running decision log in `docs/DECISIONS.md` and do not call a composite score a probability.

The brief is intentionally strict on data leakage, queue/no-fill behavior, Iranian price-limit constraints, probability calibration and broker isolation.
