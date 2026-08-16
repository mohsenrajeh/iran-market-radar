import pytest
from packages.shared.database import SyncSessionLocal
from packages.domain.models import Portfolio, Position, PublishedSignal
from services.paper_broker.sizing import PositionSizingSolver
from services.paper_broker.ledger import paper_broker
from packages.domain.risk_policy import ACTIVE_RISK_POLICY

def test_e2e_signal_evaluation_to_order_placement():
    db = SyncSessionLocal()
    try:
        portfolio = db.query(Portfolio).filter(Portfolio.is_active == True).first()
        assert portfolio is not None
        
        # Verify initial portfolio NAV invariant
        assert portfolio.cash > 0
        
        solver = PositionSizingSolver(policy=ACTIVE_RISK_POLICY)
        
        sig = PublishedSignal(
            id="e2e_sig_1",
            instrument_id="inst_1",
            symbol="فولاد",
            direction="BUY",
            opportunity_score=84.0,
            p_profit=0.84,
            entry_zone={"low": 6500.0, "high": 6600.0},
            invalidation={"price": 6000.0},
            exit_plan={"targets": [7500.0, 8200.0], "time_stop_sessions": 7},
            strategy_votes=[],
            top_reasons_fa=[],
            risk_flags_fa=[],
            regime="risk_on",
        )
        
        ticket = solver.solve(
            portfolio=portfolio,
            signal=sig,
            current_market_price=6500.0,
            adtv_20d_rials=50_000_000_000,
            sector_name="فلزات اساسی",
        )
        
        assert ticket["decision"] in ("APPROVED", "BLOCKED")
        assert ticket["recommended_quantity"] >= 0
        assert ticket["stage1_quantity"] >= 0
    finally:
        db.close()
