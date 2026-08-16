# Codex Master Prompt

You are the principal engineer implementing **Iran Market Radar**. Treat every file in this briefing directory as the product/architecture contract. Read `AGENTS.md` first, then every file under `docs/`, `config/`, and `schemas/` before coding.

## Objective
Create a production-capable, Dockerized system that continuously ingests Iranian capital-market data, computes canonical features, evaluates a diversified set of strategies, calibrates the probability of profitable outcomes, ranks opportunities, backtests them realistically, exposes the output through an API and Persian RTL dashboard, and records paper trades. The architecture must be ready for a future authorized broker API without coupling research logic to the broker.

## Phase-1 hard boundary
Do **not** place real orders. Implement `BrokerAdapter`, `ExecutionEngine` and paper broker contracts, but keep live mode fail-closed. Analysis and paper trading must be fully operational.

## Required first runnable milestone
From a clean machine with Docker:

1. `docker compose up -d --build`
2. database migrates automatically or through one documented command;
3. collector can sync instrument master and historical data from a configured adapter;
4. scheduler runs recurring ingestion;
5. feature engine computes features for all eligible symbols;
6. at least the core strategies execute;
7. signal scorer produces ranked opportunities;
8. API returns them;
9. web UI displays them in Persian RTL;
10. a backtest can be launched and its metrics inspected;
11. paper portfolio can consume an approved signal and simulate entry/exit.

## Implementation sequence

Follow `docs/15_IMPLEMENTATION_ROADMAP.md`. Do not start ML before canonical data, data-quality checks and deterministic baseline strategies are correct. Do not start broker integration before paper execution passes invariants.

## Important quantitative requirements

- Use adjusted and raw price representations separately; never destroy raw prices.
- Every feature and label has explicit timestamp semantics.
- Label definition must include estimated costs and executable horizon.
- Use rolling/walk-forward training and validation; no random train/test split for time series.
- Calibration is trained only on validation/OOS predictions, never on the same observations used to fit the predictor.
- Store calibration curves/Brier score/log loss and reliability by probability bucket.
- Opportunity Score is not the same as probability.
- Simulate next-tradable-bar execution by default; never fill at the same close used to generate a close-based signal.
- Add queue/no-fill and participation-limit models for price-limited Iranian instruments.
- Include suspended/delisted historical instruments when data allows; do not backtest only current survivors.

## Output quality

A top opportunity card must include at least:

```json
{
  "symbol": "...",
  "as_of": "...",
  "horizon": "5d",
  "direction": "long",
  "opportunity_score": 0,
  "p_profit": 0.0,
  "confidence": 0,
  "expected_return_pct": 0.0,
  "expected_drawdown_pct": 0.0,
  "entry_zone": {"low": 0, "high": 0},
  "invalidation": {"price": 0, "reason": "..."},
  "exit_plan": {"type": "...", "targets": []},
  "liquidity_score": 0,
  "regime": "...",
  "strategy_votes": [],
  "top_reasons_fa": [],
  "risk_flags_fa": [],
  "data_quality": 0,
  "model_version": "...",
  "strategy_version": "..."
}
```

## UI language

The primary UI is Persian and RTL. Internal code, identifiers and comments may be English. All user-visible numerical meanings must be explicit; never show an unlabeled “confidence percent” that could be mistaken for probability of profit.

## Stop conditions

Treat these as blockers, not TODOs:
- data leakage;
- impossible historical fill assumptions;
- arbitrary percentage labels;
- duplicate ingestion corruption;
- strategies using unavailable future data;
- live trading enabled without explicit authorized adapter and risk gates;
- secrets committed to git.

At the end of each milestone, update `docs/DECISIONS.md`, run all tests, and provide a concise implementation status with remaining risks.
