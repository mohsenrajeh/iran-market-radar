import pytest
from packages.domain.models import BrokerOrder, Position
from services.paper_broker.execution import ExecutionSimulator, ExecutionBar

def test_simulate_order_fill_normal():
    sim = ExecutionSimulator()
    
    order = BrokerOrder(
        id="ord_1",
        portfolio_id="port_1",
        symbol="فولاد",
        side="BUY",
        order_type="LIMIT",
        price=5050.0,
        quantity=10000,
        status="SUBMITTED",
    )
    
    next_bar: ExecutionBar = {
        "trading_date": "2026-08-16",
        "open": 5020.0,
        "high": 5100.0,
        "low": 4980.0,
        "close": 5050.0,
        "volume": 1_000_000,
        "value": 5_050_000_000.0,
        "allowed_min": 4750.0,
        "allowed_max": 5250.0,
    }
    
    fill, msg = sim.simulate_order_fill(order=order, next_bar=next_bar)
    
    assert fill is not None
    assert fill.quantity > 0
    assert fill.fill_price >= 5020.0
    assert fill.fees_rials > 0
    assert order.status in ("FILLED", "PARTIALLY_FILLED")

def test_simulate_order_fill_limit_up_rejected():
    sim = ExecutionSimulator()
    
    order = BrokerOrder(
        id="ord_2",
        portfolio_id="port_1",
        symbol="فولاد",
        side="BUY",
        order_type="LIMIT",
        price=5250.0,
        quantity=100000,
        status="SUBMITTED",
    )
    
    next_bar: ExecutionBar = {
        "trading_date": "2026-08-16",
        "open": 5250.0,
        "high": 5250.0,
        "low": 5250.0,
        "close": 5250.0,
        "volume": 1000,
        "value": 5_250_000.0,
        "allowed_min": 4750.0,
        "allowed_max": 5250.0,
    }
    
    fill, msg = sim.simulate_order_fill(order=order, next_bar=next_bar, is_limit_up_locked=True)
    
    assert fill is None
    assert order.status == "REJECTED"
    assert "صف خرید" in msg

def test_evaluate_position_exit_stop_loss():
    sim = ExecutionSimulator()
    
    pos = Position(
        id="pos_1",
        portfolio_id="port_1",
        symbol="فولاد",
        quantity=10000,
        average_entry_price=5000.0,
        current_price=4700.0,
        stop_loss=4750.0,  # Stop breached
        target_price=5800.0,
        is_open=True,
    )
    
    current_bar: ExecutionBar = {
        "trading_date": "2026-08-16",
        "open": 4800.0,
        "high": 4820.0,
        "low": 4690.0,
        "close": 4700.0,
        "volume": 500_000,
        "value": 2_350_000_000.0,
        "allowed_min": 4500.0,
        "allowed_max": 5100.0,
    }
    
    action, exit_price, exit_ratio = sim.evaluate_exits_and_trailing_stop(
        position=pos,
        current_bar=current_bar,
        initial_risk_rials=250.0,
        holding_sessions=3,
    )
    
    assert action == "STOP_LOSS"
    assert exit_ratio == 1.0
    assert exit_price == 4750.0


def test_limit_order_waits_when_price_never_touches_limit():
    sim = ExecutionSimulator()
    order = BrokerOrder(
        id="ord_wait", portfolio_id="port_1", symbol="فولاد", side="BUY",
        order_type="LIMIT", price=5000.0, quantity=1000, filled_quantity=0, status="SUBMITTED",
    )
    bar: ExecutionBar = {
        "trading_date": "2026-08-17", "open": 5200.0, "high": 5300.0,
        "low": 5100.0, "close": 5250.0, "volume": 1_000_000,
        "value": 5_250_000_000.0, "allowed_min": 4900.0, "allowed_max": 5400.0,
    }
    fill, message = sim.simulate_order_fill(order, bar)
    assert fill is None
    assert order.status == "SUBMITTED"
    assert "در صف" in message


def test_partial_fill_uses_remaining_quantity_only():
    sim = ExecutionSimulator()
    order = BrokerOrder(
        id="ord_partial", portfolio_id="port_1", symbol="فولاد", side="SELL",
        order_type="TRIM", price=5000.0, quantity=1000, filled_quantity=400,
        status="PARTIALLY_FILLED",
    )
    bar: ExecutionBar = {
        "trading_date": "2026-08-17", "open": 5050.0, "high": 5100.0,
        "low": 4950.0, "close": 5030.0, "volume": 100_000,
        "value": 503_000_000.0, "allowed_min": 4750.0, "allowed_max": 5250.0,
    }
    fill, _ = sim.simulate_order_fill(order, bar)
    assert fill is not None
    assert fill.quantity == 600
    assert order.filled_quantity == 1000
    assert order.status == "FILLED"
