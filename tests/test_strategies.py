"""Unit tests for strategy evaluation and registry."""
from packages.strategies.base import StrategyContext
from packages.strategies.registry import strategy_registry


def test_strategy_registry_execution():
    ctx = StrategyContext(
        symbol="فولاد",
        instrument_id="inst_folad",
        name_fa="فولاد مبارکه",
        market="TSE",
        sector_name="فلزات اساسی",
        horizon="5d",
        features={
            "close": 5800.0,
            "ret_20d": 0.08,
            "ret_60d": 0.14,
            "ema_trend_score": 1.0,
            "ema_20": 5600.0,
            "atr_14": 120.0,
            "dist_to_20_high": 0.002,
            "vol_z_score_20d": 1.8,
            "real_buyer_power_ratio": 1.55,
            "net_real_inflow_pct": 0.12,
            "volume_ratio_20d": 2.2,
            "ret_1d": 0.02,
        },
        market_regime="risk_on",
        allowed_min=5510.0,
        allowed_max=6090.0,
    )

    candidates = strategy_registry.evaluate_all(ctx)
    assert len(candidates) >= 3  # Momentum, Breakout, ClientFlow should trigger
    strat_keys = [c.strategy_key for c in candidates]
    assert "cross_sectional_momentum" in strat_keys
    assert "client_flow" in strat_keys
