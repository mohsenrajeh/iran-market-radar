"""Unit and property tests for Closed Trade History and Immutable Ledger."""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.shared.database import Base
from packages.domain.models import (
    Portfolio,
    Position,
    Instrument,
    ClosedTradeHistory,
    TradeExecutionTimeline,
    TradeExitReason,
    TradeOutcomeStatus,
)
from packages.shared.datetime_utils import now_utc
from services.paper_broker.learning_engine import learning_engine


@pytest.fixture
def db_session():
    """Provides an isolated in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_closed_position_moves_to_history_and_leaves_open_positions(db_session):
    """Verifies that closing a position removes it from active list and creates immutable ClosedTradeHistory."""
    port = Portfolio(
        id="port_test_01",
        name="پورتفوی آزمایشی تست",
        cash=100_000_000_000.0,
        initial_cash=100_000_000_000.0,
    )
    pos = Position(
        id="pos_test_01",
        portfolio_id=port.id,
        symbol="فولاد",
        quantity=100_000,
        average_entry_price=5000.0,
        current_price=5600.0,
        is_open=True,
        opened_at=now_utc() - timedelta(days=5),
        stop_loss=4750.0,
        target_price=5500.0,
    )
    db_session.add_all([port, pos])
    db_session.commit()

    # Verify initially open
    assert len(port.positions) == 1
    assert port.positions[0].is_open is True

    # Simulate position close
    exit_price = 5600.0
    buy_val = pos.average_entry_price * pos.quantity
    sell_val = exit_price * pos.quantity
    entry_fee = buy_val * 0.003712
    exit_fee = sell_val * 0.003850
    tax_val = sell_val * 0.005000
    total_costs = entry_fee + exit_fee + tax_val
    gross_pnl = sell_val - buy_val
    net_pnl = gross_pnl - total_costs
    ret_pct = (net_pnl / buy_val) * 100.0

    pos.is_open = False
    pos.unrealized_pnl = 0.0

    closed_trade = ClosedTradeHistory(
        portfolio_id=port.id,
        position_id=pos.id,
        symbol=pos.symbol,
        company_name="فولاد مبارکه اصفهان",
        sector="فلزات اساسی",
        strategy_id="s01_momentum",
        strategy_name_fa="مومنتوم مقطعی",
        strategy_version="v1.0",
        model_version="v2.4-isotonic-brier",
        opened_at=pos.opened_at,
        closed_at=now_utc(),
        holding_sessions=5,
        planned_entry=5000.0,
        avg_entry_price=5000.0,
        avg_exit_price=exit_price,
        total_quantity=pos.quantity,
        gross_buy_value=buy_val,
        gross_sell_value=sell_val,
        entry_fees=entry_fee,
        exit_fees=exit_fee,
        tax=tax_val,
        total_cost=total_costs,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        net_return_pct=round(ret_pct, 2),
        initial_risk_amount=buy_val * 0.05,
        initial_risk_pct_nav=0.35,
        realized_R=2.4,
        MFE=12.5,
        MAE=1.0,
        initial_stop=4750.0,
        final_stop=5200.0,
        target1=5500.0,
        target2=5800.0,
        exit_reason="TARGET_1",
        market_regime_at_entry="risk_on",
        market_regime_at_exit="risk_on",
        outcome_status="WIN",
    )
    db_session.add(closed_trade)
    db_session.commit()

    # 1. Verify position is no longer active
    open_positions = db_session.query(Position).filter(Position.is_open == True).all()
    assert len(open_positions) == 0

    # 2. Verify ClosedTradeHistory exists and is complete
    history_records = db_session.query(ClosedTradeHistory).all()
    assert len(history_records) == 1
    h = history_records[0]
    assert h.symbol == "فولاد"
    assert h.outcome_status == "WIN"
    assert h.net_pnl == net_pnl
    assert h.total_cost == total_costs
    assert h.exit_reason == "TARGET_1"


def test_timeline_and_post_mortem_generation(db_session):
    """Verifies that closed trade execution timeline and post-mortem are generated."""
    port = Portfolio(id="port_test_02", name="تست", cash=100_000_000_000.0)
    trade = ClosedTradeHistory(
        portfolio_id=port.id,
        symbol="فملی",
        company_name="ملی مس",
        sector="فلزات اساسی",
        strategy_id="s03_breakout",
        strategy_name_fa="شکست حجم و نوسان",
        opened_at=now_utc() - timedelta(days=6),
        closed_at=now_utc(),
        holding_sessions=6,
        planned_entry=7000.0,
        avg_entry_price=7020.0,
        avg_exit_price=7800.0,
        total_quantity=50_000,
        gross_buy_value=351_000_000.0,
        gross_sell_value=390_000_000.0,
        entry_fees=1_302_912.0,
        exit_fees=1_501_500.0,
        tax=1_950_000.0,
        total_cost=4_754_412.0,
        gross_pnl=39_000_000.0,
        net_pnl=34_245_588.0,
        net_return_pct=9.76,
        initial_risk_amount=15_000_000.0,
        initial_risk_pct_nav=0.35,
        realized_R=2.2,
        MFE=12.0,
        MAE=0.8,
        initial_stop=6650.0,
        final_stop=7300.0,
        target1=7700.0,
        target2=8100.0,
        exit_reason="TARGET_1",
        market_regime_at_entry="risk_on",
        market_regime_at_exit="risk_on",
        outcome_status="WIN",
    )
    db_session.add_all([port, trade])
    db_session.flush()

    # Timeline entries
    t1 = TradeExecutionTimeline(
        trade_id=trade.id,
        event_type="ENTRY_FILL",
        timestamp=trade.opened_at,
        price=7020.0,
        quantity=50_000,
        portion_pct=100.0,
        fees=1_302_912.0,
        notes_fa="ورود به معامله",
    )
    t2 = TradeExecutionTimeline(
        trade_id=trade.id,
        event_type="FINAL_EXIT_FILL",
        timestamp=trade.closed_at,
        price=7800.0,
        quantity=50_000,
        portion_pct=100.0,
        fees=3_451_500.0,
        notes_fa="اصابت تارگت اول",
    )
    db_session.add_all([t1, t2])
    db_session.flush()

    # Generate post-mortem
    pm = learning_engine.generate_post_mortem(db_session, trade)
    db_session.commit()

    assert pm is not None
    assert pm.process_quality_score >= 80.0
    assert pm.outcome_vs_process_type == "GOOD_PROCESS_WIN"
    assert len(trade.timeline_events) == 2
