import pytest
from packages.domain.risk_policy import ACTIVE_RISK_POLICY
from packages.domain.models import Portfolio, Position, PublishedSignal
from services.paper_broker.sizing import PositionSizingSolver

def test_position_sizing_solver_normal_approved():
    solver = PositionSizingSolver(policy=ACTIVE_RISK_POLICY)
    
    port = Portfolio(
        id="test_port_1",
        name="Test Portfolio",
        initial_cash=50_000_000_000,
        cash=49_000_000_000,
        kill_switch_active=False,
    )
    port.positions = []
    
    sig = PublishedSignal(
        id="sig_1",
        instrument_id="inst_1",
        symbol="فولاد",
        direction="BUY",
        opportunity_score=82.0,
        p_profit=0.82,
        entry_zone={"low": 6500.0, "high": 6600.0},
        invalidation={"price": 6000.0},
        exit_plan={"targets": [7500.0, 8200.0], "time_stop_sessions": 7},
        strategy_votes=[],
        top_reasons_fa=[],
        risk_flags_fa=[],
        regime="risk_on",
    )
    
    ticket = solver.solve(
        portfolio=port,
        signal=sig,
        current_market_price=6500.0,
        adtv_20d_rials=50_000_000_000,
        sector_name="فلزات اساسی",
    )
    
    assert ticket["decision"] == "APPROVED"
    assert ticket["recommended_quantity"] > 0
    assert ticket["stage1_quantity"] > 0
    assert ticket["recommended_weight_pct"] <= 10.0
    assert ticket["gross_exposure_after_trade_pct"] <= 70.0
    assert ticket["sector_exposure_after_trade_pct"] <= 18.0

def test_position_sizing_blocked_by_kill_switch():
    solver = PositionSizingSolver(policy=ACTIVE_RISK_POLICY)
    
    port = Portfolio(
        id="test_port_2",
        name="Test Portfolio",
        initial_cash=50_000_000_000,
        cash=49_000_000_000,
        kill_switch_active=True,
    )
    port.positions = []
    
    sig = PublishedSignal(
        id="sig_2",
        instrument_id="inst_2",
        symbol="نوری",
        direction="BUY",
        opportunity_score=78.0,
        p_profit=0.78,
        entry_zone={"low": 12000.0, "high": 12200.0},
        invalidation={"price": 11200.0},
        exit_plan={"targets": [13800.0, 15000.0], "time_stop_sessions": 5},
        strategy_votes=[],
        top_reasons_fa=[],
        risk_flags_fa=[],
        regime="risk_off",
    )
    
    ticket = solver.solve(
        portfolio=port,
        signal=sig,
        current_market_price=12000.0,
        adtv_20d_rials=80_000_000_000,
        sector_name="محصولات شیمیایی",
    )
    
    assert ticket["decision"] == "BLOCKED"
    assert "Kill Switch" in ticket["decision_reason_fa"] or "اضطراری" in ticket["decision_reason_fa"]
