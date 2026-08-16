import pytest
from packages.shared.metrics import compute_r_multiples

def test_compute_r_multiples_basic():
    # Planned entry 10,000, Stop 9,000 (1R = 1,000), Target1 12,000 (2R gross)
    metrics = compute_r_multiples(
        current_price=10100.0,
        planned_entry=10000.0,
        stop_price=9000.0,
        target1_price=12000.0,
        target2_price=13500.0,
    )
    
    assert metrics["initial_risk_rials"] == 1000.0
    assert metrics["stop_pct"] == -10.0
    assert metrics["target1_pct"] == 20.0
    assert metrics["current_r"] == 0.1
    assert metrics["gross_reward_risk_ratio"] == 2.0
    assert metrics["net_reward_risk_ratio"] > 1.5  # Accounts for 1.2562% fees + 20 bps slippage
    assert metrics["entry_state"] == "READY"

def test_chase_prevention_trigger():
    # Price ran up past +0.35R
    metrics = compute_r_multiples(
        current_price=10400.0,  # +0.40R
        planned_entry=10000.0,
        stop_price=9000.0,  # 1R = 1,000
        target1_price=12000.0,
        target2_price=13500.0,
    )
    assert metrics["current_r"] == 0.4
    assert metrics["entry_state"] == "CHASE_BLOCKED"
    assert "فرار" in metrics["entry_state_reason_fa"]
