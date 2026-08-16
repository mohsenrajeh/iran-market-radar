import pytest
from packages.domain.risk_policy import ACTIVE_RISK_POLICY

def test_active_risk_policy_constants():
    policy = ACTIVE_RISK_POLICY
    assert policy.policy_id == "POL-TSE-2026-V2.5"
    assert policy.version == "2.5.0-ENTERPRISE"
    assert policy.drawdown_ladder.dd_kill_switch_pct == 12.0
    assert policy.portfolio_limits.sector_exposure_cap_pct == 18.0
    assert policy.portfolio_limits.correlated_cluster_cap_pct == 20.0
    assert policy.portfolio_limits.max_active_positions == 10
    assert policy.tse_equity_roundtrip_fee_pct == 1.2562

def test_regime_parameter_lookup():
    policy = ACTIVE_RISK_POLICY
    
    risk_on = policy.regimes["RISK_ON"]
    assert risk_on.max_gross_exposure_pct == 70.0
    assert risk_on.min_cash_reserve_pct == 30.0
    assert risk_on.risk_per_trade_pct == 0.35

    neutral = policy.regimes["NEUTRAL"]
    assert neutral.max_gross_exposure_pct == 50.0
    assert neutral.min_cash_reserve_pct == 50.0
    assert neutral.risk_per_trade_pct == 0.25

    risk_off = policy.regimes["RISK_OFF"]
    assert risk_off.max_gross_exposure_pct == 25.0
    assert risk_off.min_cash_reserve_pct == 75.0
    assert risk_off.risk_per_trade_pct == 0.15

    halted = policy.regimes["HALTED"]
    assert halted.max_gross_exposure_pct == 0.0
    assert halted.min_cash_reserve_pct == 100.0
    assert halted.risk_per_trade_pct == 0.0
