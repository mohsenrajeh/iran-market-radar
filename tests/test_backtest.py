"""Unit tests for backtest simulation engine."""
from packages.data_adapters.fixtures import FixtureReplayAdapter
from services.backtester.engine import run_backtest_simulation
import pytest


@pytest.mark.asyncio
async def test_backtest_simulation_execution():
    adapter = FixtureReplayAdapter(seed=42)
    bars_folad = await adapter.fetch_eod_history("فولاد", days=100)
    bars_femli = await adapter.fetch_eod_history("فملی", days=100)

    symbol_bars_map = {
        "فولاد": bars_folad,
        "فملی": bars_femli,
    }

    run_obj, trades, eq_curve = run_backtest_simulation(
        name="تست اعتبارسنجی بک‌تست",
        strategy_key="cross_sectional_momentum",
        symbol_bars_map=symbol_bars_map,
        initial_capital=1_000_000_000.0,
        horizon_sessions=5,
    )

    assert run_obj.status == "COMPLETED"
    assert len(eq_curve) > 0
    assert run_obj.initial_capital == 1_000_000_000.0
    assert run_obj.trade_count == len(trades)
