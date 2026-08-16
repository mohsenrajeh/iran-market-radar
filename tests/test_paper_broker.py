"""Unit tests for Paper Broker and Risk Gatekeeper."""
from packages.domain.models import Portfolio, PublishedSignal
from services.paper_broker.ledger import PaperBrokerService
from packages.shared.datetime_utils import now_utc


def test_paper_broker_position_sizing_and_risk():
    broker = PaperBrokerService()
    port = Portfolio(
        id="port_test",
        cash=1_000_000_000.0,
        initial_cash=1_000_000_000.0,
        positions=[],
        kill_switch_active=False,
    )

    # 1. Calculate sizing: Entry 10,000, Stop 9,500
    qty = broker.calculate_position_size(port, entry_price=10000.0, stop_price=9500.0, opportunity_score=85.0)
    assert qty > 0
    assert (qty * 10000.0) <= (port.cash * 0.10)  # Capped at symbol cap (10% NAV)

    # 2. Test Order Creation from Signal
    sig = PublishedSignal(
        id="sig_test_1",
        instrument_id="inst_test",
        symbol="فولاد",
        name_fa="فولاد مبارکه",
        market="TSE",
        as_of=now_utc(),
        horizon="5d",
        direction="long",
        actionable=True,
        grade="A",
        opportunity_score=85.0,
        p_profit=0.68,
        confidence=78.0,
        signal_strength=92.0,
        entry_zone={"low": 9900, "high": 10100},
        invalidation={"price": 9500, "reason_fa": "حد ضرر"},
        exit_plan={"type": "targets", "targets": [11000]},
        liquidity_score=80.0,
        fill_probability_score=80.0,
        data_quality=95.0,
        strategy_votes=[],
        top_reasons_fa=["مومنتوم قوی"],
        risk_flags_fa=[],
    )

    order, msg = broker.create_order_from_signal(port, sig, current_market_price=10000.0, quantity=qty)
    assert order is not None
    assert len(port.positions) == 1
    assert port.cash < 1_000_000_000.0


def test_kill_switch_blocks_orders():
    broker = PaperBrokerService()
    port = Portfolio(id="port_test2", cash=1_000_000_000.0, initial_cash=1_000_000_000.0, kill_switch_active=True, positions=[])
    sig = PublishedSignal(
        id="sig_test_2",
        instrument_id="inst_test",
        symbol="فولاد",
        name_fa="فولاد مبارکه",
        as_of=now_utc(),
        horizon="5d",
        actionable=True,
        opportunity_score=85.0,
        p_profit=0.68,
        confidence=78.0,
        signal_strength=92.0,
        entry_zone={"low": 9900, "high": 10100},
        invalidation={"price": 9500, "reason_fa": "حد ضرر"},
        exit_plan={"type": "targets", "targets": [11000]},
        liquidity_score=80.0,
        fill_probability_score=80.0,
        data_quality=95.0,
        strategy_votes=[],
        top_reasons_fa=[],
        risk_flags_fa=[],
    )

    order, msg = broker.create_order_from_signal(port, sig, current_market_price=10000.0)
    assert order is None
    assert "Kill-Switch" in msg or "قطع اضطراری" in msg
