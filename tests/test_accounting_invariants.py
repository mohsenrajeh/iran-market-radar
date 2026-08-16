import pytest
from packages.domain.models import Portfolio, Position
from services.paper_broker.accounting import AccountingReconciler

def test_accounting_reconciler_invariants():
    reconciler = AccountingReconciler()
    
    port = Portfolio(
        id="test_rec_port",
        name="Test Reconciled Portfolio",
        initial_cash=100_000_000_000,
        cash=45_000_000_000,
        kill_switch_active=False,
    )
    
    pos1 = Position(
        id="pos_1",
        portfolio_id="test_rec_port",
        symbol="فولاد",
        quantity=5_000_000,
        average_entry_price=6000.0,
        current_price=6500.0,
        is_open=True,
    )
    pos2 = Position(
        id="pos_2",
        portfolio_id="test_rec_port",
        symbol="نوری",
        quantity=2_000_000,
        average_entry_price=11000.0,
        current_price=11250.0,
        is_open=True,
    )
    port.positions = [pos1, pos2]
    
    is_ok, report = reconciler.reconcile_portfolio(port)
    
    assert is_ok is True
    assert report["is_reconciled"] is True
    assert report["discrepancy_rials"] < 1.0
    assert report["total_nav_rials"] == (45_000_000_000 + (5_000_000 * 6500.0) + (2_000_000 * 11250.0))
    assert report["total_nav_tomans"] == report["total_nav_rials"] / 10.0
