from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.domain.models import (
    Base, BrokerOrder, CashLedger, ClosedTradeHistory, DecisionAudit, Instrument, MarketDataBatch,
    MarketSnapshot,
    OrderFill, PaperCampaign, PaperTradeLog, Portfolio, Position, PublishedSignal, TradeExecutionTimeline,
)
from services.paper_broker.ledger import PaperBrokerService


def _official_snapshot(instrument_id: str, at: datetime, *, price: float, volume: int, suffix: str):
    batch_id = f"batch_{suffix}"
    batch = MarketDataBatch(
        id=batch_id,
        source_key="tsetmc_cdn_market_watch",
        provider_name="TSE WebGW",
        source_timestamp=at,
        received_at=at,
        mode="official",
        trust_tier="OFFICIAL_DIRECT",
        trade_eligible=True,
        schema_version="tsetmc-cdn-market-watch-v1",
        row_count=560,
        complete=True,
    )
    snapshot = MarketSnapshot(
        instrument_id=instrument_id,
        source_timestamp=at,
        last_price=price,
        close_price=price,
        high_price=price,
        low_price=price,
        yesterday_price=price,
        volume=volume,
        value=price * volume,
        trade_count=max(1, volume // 1000),
        allowed_min=price * 0.95,
        allowed_max=price * 1.05,
        state="OPEN",
        available_at=at,
        ingested_at=at,
        source_key="tsetmc_cdn_market_watch",
        batch_id=batch_id,
        trust_tier="OFFICIAL_DIRECT",
        trade_eligible=True,
    )
    return batch, snapshot


def test_full_exit_changes_nothing_until_later_official_snapshot():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    broker = PaperBrokerService()
    opened_at = datetime(2026, 8, 16, 6, 0, tzinfo=timezone.utc)
    try:
        portfolio = Portfolio(
            id="port_pending_exit", name="test", mode="paper", cash=90_000.0,
            initial_cash=100_000.0, realized_pnl=0.0, kill_switch_active=False,
        )
        instrument = Instrument(
            id="inst_pending_exit", source_instrument_code="123", isin="IRO1TEST0001", ticker="فولاد",
            ticker_normalized="فولاد", name_fa="فولاد", market="TSE", board="main",
            base_volume=1, is_active=True,
        )
        position = Position(
            id="pos_pending_exit", portfolio_id=portfolio.id, symbol="فولاد", quantity=100,
            average_entry_price=100.0, current_price=100.0, total_invested_rials=10_037.12,
            stop_loss=95.0, target_price=112.0, decision_method="multi_family_confluence",
            entry_reason_fa="تست", opened_at=opened_at, is_open=True,
        )
        trade_log = PaperTradeLog(
            portfolio_id=portfolio.id, symbol="فولاد", side="BUY", entry_price=100.0,
            quantity=100, total_invested_rials=10_037.12, entry_at=opened_at,
            reason_fa="تست", is_closed=False,
        )
        session.add_all([portfolio, instrument, position, trade_log])
        session.commit()
        portfolio = session.query(Portfolio).filter_by(id=portfolio.id).one()

        order, _ = broker.create_exit_order(portfolio, position.id, current_price=100.0, ratio=1.0)
        assert order is not None
        order.created_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        order.updated_at = order.created_at
        session.add(order)
        session.commit()

        unchanged = session.query(Portfolio).filter_by(id=portfolio.id).one()
        assert unchanged.cash == 90_000.0
        assert session.query(Position).filter_by(id=position.id).one().is_open is True
        assert session.query(OrderFill).count() == 0

        order = session.query(BrokerOrder).filter_by(id=order.id).one()
        snapshot_at = order.created_at + timedelta(seconds=10)
        prior_batch, prior_snapshot = _official_snapshot(
            instrument.id, order.created_at - timedelta(seconds=1),
            price=100.0, volume=900_000, suffix="exit_prior",
        )
        fill_batch, fill_snapshot = _official_snapshot(
            instrument.id, snapshot_at, price=110.0, volume=1_000_000, suffix="exit_fill",
        )
        session.add_all([prior_batch, prior_snapshot, fill_batch, fill_snapshot])
        session.commit()

        result = broker.process_pending_orders(session, unchanged)
        session.commit()

        assert result["filled"] == 1
        assert session.query(BrokerOrder).filter_by(id=order.id).one().status == "FILLED"
        assert session.query(Position).filter_by(id=position.id).one().is_open is False
        assert session.query(OrderFill).filter_by(order_id=order.id).count() == 1
        assert session.query(CashLedger).filter_by(reference_id=order.id).count() == 1
        assert session.query(ClosedTradeHistory).filter_by(position_id=position.id).count() == 1
        assert session.query(Portfolio).filter_by(id=portfolio.id).one().cash > 90_000.0
    finally:
        session.close()

def test_entry_to_exit_history_preserves_signal_snapshot_and_exact_targets():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    broker = PaperBrokerService()
    submitted_at = datetime.now(timezone.utc) - timedelta(seconds=30)
    try:
        portfolio = Portfolio(
            id="port_provenance", name="test", mode="paper", cash=1_000_000.0,
            initial_cash=1_000_000.0, realized_pnl=0.0, kill_switch_active=False,
        )
        instrument = Instrument(
            id="inst_provenance", source_instrument_code="456", isin="IRO1TEST0002", ticker="فملی",
            ticker_normalized="فملی", name_fa="ملی مس", market="TSE", board="main",
            base_volume=1, is_active=True,
        )
        signal = PublishedSignal(
            id="sig_provenance", instrument_id=instrument.id, symbol="فملی", name_fa="ملی مس",
            market="TSE", as_of=submitted_at, actionable=True, grade="A", opportunity_score=88.0,
            p_profit=0.72, confidence=81.0, signal_strength=95.0, current_price=100.0,
            entry_zone={"low": 99.0, "high": 101.0, "max_chase": 102.0},
            invalidation={"price": 95.0},
            exit_plan={"targets": [110.0, 118.0], "time_stop_sessions": 7},
            liquidity_score=90.0, fill_probability_score=90.0, data_quality=100.0,
            regime="neutral", strategy_votes=[{"strategy": "breakout_volume", "vote": 0.9}],
            top_reasons_fa=["شکست معتبر"], risk_flags_fa=[],
            decision_components={"technical_gate": {"qualifying_families": ["breakout_volatility"]}},
            model_version="isotonic-oos-test", strategy_version="breakout_volume@1.0.0",
            calibration_version="isotonic-oos-test",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        entry_order = BrokerOrder(
            id="ord_entry_provenance", portfolio_id=portfolio.id, signal_id=signal.id,
            symbol=signal.symbol, side="BUY", order_type="LIMIT", price=100.0,
            quantity=100, filled_quantity=0, status="SUBMITTED", created_at=submitted_at,
            updated_at=submitted_at,
        )
        campaign = PaperCampaign(
            id="campaign_provenance", portfolio_id=portfolio.id, name_fa="تست",
            status="RUNNING", starts_at=submitted_at - timedelta(days=1),
            ends_at=submitted_at + timedelta(days=29), initial_capital_rials=portfolio.initial_cash,
            config_snapshot={"paper_only": True},
        )
        entry_snapshot_at = submitted_at + timedelta(seconds=10)
        prior_batch, prior_snapshot = _official_snapshot(
            instrument.id, submitted_at - timedelta(seconds=1),
            price=99.0, volume=900_000, suffix="entry_prior",
        )
        entry_batch, entry_snapshot = _official_snapshot(
            instrument.id, entry_snapshot_at, price=100.0, volume=1_000_000, suffix="entry_fill",
        )
        session.add_all([
            portfolio, campaign, instrument, signal, entry_order,
            prior_batch, prior_snapshot, entry_batch, entry_snapshot,
        ])
        session.commit()

        assert broker.process_pending_orders(session, portfolio)["filled"] == 1
        session.commit()
        position = session.query(Position).filter_by(portfolio_id=portfolio.id, is_open=True).one()
        exit_order, _ = broker.create_exit_order(portfolio, position.id, current_price=110.0, ratio=1.0)
        assert exit_order is not None
        exit_order.created_at = datetime.now(timezone.utc) - timedelta(seconds=20)
        exit_order.updated_at = exit_order.created_at
        session.add(exit_order)
        session.commit()

        exit_snapshot_at = exit_order.created_at + timedelta(seconds=10)
        exit_prior_batch, exit_prior_snapshot = _official_snapshot(
            instrument.id, exit_order.created_at - timedelta(seconds=1),
            price=100.0, volume=1_500_000, suffix="final_exit_prior",
        )
        exit_batch, exit_snapshot = _official_snapshot(
            instrument.id, exit_snapshot_at, price=110.0, volume=2_000_000, suffix="final_exit_fill",
        )
        session.add_all([exit_prior_batch, exit_prior_snapshot, exit_batch, exit_snapshot])
        session.commit()

        assert broker.process_pending_orders(session, portfolio)["filled"] == 1
        session.commit()
        closed = session.query(ClosedTradeHistory).one()
        assert closed.signal_id == signal.id
        assert closed.decision_id is not None
        assert closed.model_version == "isotonic-oos-test"
        assert closed.dataset_version == f"market_snapshot:{entry_snapshot_at.isoformat()}"
        assert closed.target1 == 110.0
        assert closed.target2 == 118.0
        assert closed.MFE == (110.0 - closed.avg_entry_price) / closed.avg_entry_price * 100.0
        assert closed.MAE == (closed.avg_entry_price - 100.0) / closed.avg_entry_price * 100.0
        assert closed.portfolio_nav_at_entry == 1_000_000.0
        event_types = [row.event_type for row in session.query(TradeExecutionTimeline).order_by(TradeExecutionTimeline.timestamp).all()]
        assert event_types == ["ENTRY_FILL", "FINAL_EXIT_FILL"]
        assert session.query(DecisionAudit).count() >= 2
    finally:
        session.close()


def test_sell_only_pass_leaves_pending_buy_and_expired_signal_is_rejected_before_fill():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    broker = PaperBrokerService()
    now = datetime.now(timezone.utc)
    try:
        portfolio = Portfolio(
            id="port_expired_buy", name="test", mode="paper", cash=1_000_000,
            initial_cash=1_000_000, realized_pnl=0, kill_switch_active=False,
        )
        signal = PublishedSignal(
            id="sig_expired_buy", instrument_id="inst_expired_buy", symbol="وبملت",
            name_fa="بانک ملت", market="TSE", as_of=now - timedelta(minutes=5),
            expires_at=now - timedelta(seconds=1), actionable=True, grade="A",
            opportunity_score=90, p_profit=0.7, confidence=80, signal_strength=90,
            current_price=100, entry_zone={"low": 99, "high": 101},
            invalidation={"price": 95}, exit_plan={"targets": [110]},
            liquidity_score=90, fill_probability_score=90, data_quality=100,
            regime="neutral", strategy_votes=[], top_reasons_fa=[], risk_flags_fa=[],
            decision_components={}, model_version="test", strategy_version="test",
        )
        order = BrokerOrder(
            id="ord_expired_buy", portfolio_id=portfolio.id, signal_id=signal.id,
            symbol=signal.symbol, side="BUY", order_type="LIMIT", price=100,
            quantity=10, filled_quantity=0, status="SUBMITTED",
            created_at=now - timedelta(seconds=30), updated_at=now - timedelta(seconds=30),
        )
        campaign = PaperCampaign(
            id="campaign_expired_signal", portfolio_id=portfolio.id, name_fa="تست",
            status="RUNNING", starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=29), initial_capital_rials=portfolio.initial_cash,
            config_snapshot={"paper_only": True},
        )
        session.add_all([portfolio, campaign, signal, order])
        session.commit()

        sell_pass = broker.process_pending_orders(session, portfolio, allowed_sides={"SELL"})
        session.commit()
        assert sell_pass["filled"] == 0
        assert session.get(BrokerOrder, order.id).status == "SUBMITTED"

        buy_pass = broker.process_pending_orders(session, portfolio, allowed_sides={"BUY"})
        session.commit()
        assert buy_pass["filled"] == 0
        assert session.get(BrokerOrder, order.id).status == "REJECTED"
        assert session.query(OrderFill).count() == 0
    finally:
        session.close()


def test_kill_switch_rejects_pending_buy_before_snapshot_or_cash_mutation():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    broker = PaperBrokerService()
    now = datetime.now(timezone.utc)
    try:
        portfolio = Portfolio(
            id="port_killed_buy", name="test", mode="paper", cash=1_000_000,
            initial_cash=1_000_000, realized_pnl=0, kill_switch_active=True,
        )
        order = BrokerOrder(
            id="ord_killed_buy", portfolio_id=portfolio.id, signal_id="position:pos_any",
            symbol="فولاد", side="BUY", order_type="SCALE_IN", price=100,
            quantity=10, filled_quantity=0, status="SUBMITTED",
            created_at=now - timedelta(seconds=30), updated_at=now - timedelta(seconds=30),
        )
        campaign = PaperCampaign(
            id="campaign_killed_buy", portfolio_id=portfolio.id, name_fa="تست",
            status="RUNNING", starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=29), initial_capital_rials=portfolio.initial_cash,
            config_snapshot={"paper_only": True},
        )
        session.add_all([portfolio, campaign, order])
        session.commit()

        result = broker.process_pending_orders(session, portfolio, allowed_sides={"BUY"})
        session.commit()
        assert result["filled"] == 0
        assert session.get(BrokerOrder, order.id).status == "REJECTED"
        assert session.get(Portfolio, portfolio.id).cash == 1_000_000
        assert session.query(OrderFill).count() == 0
    finally:
        session.close()


def test_expired_campaign_rejects_queued_buy_but_does_not_touch_cash():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    broker = PaperBrokerService()
    now = datetime.now(timezone.utc)
    try:
        portfolio = Portfolio(
            id="port_expired_campaign_buy", name="test", mode="paper", cash=1_000_000,
            initial_cash=1_000_000, realized_pnl=0, kill_switch_active=False,
        )
        campaign = PaperCampaign(
            id="campaign_expired_buy", portfolio_id=portfolio.id, name_fa="تست",
            status="RUNNING", starts_at=now - timedelta(days=31),
            ends_at=now - timedelta(days=1), initial_capital_rials=portfolio.initial_cash,
            config_snapshot={"paper_only": True},
        )
        order = BrokerOrder(
            id="ord_expired_campaign_buy", portfolio_id=portfolio.id,
            signal_id="position:pos_any", symbol="فولاد", side="BUY",
            order_type="SCALE_IN", price=100, quantity=10, filled_quantity=0,
            status="SUBMITTED", created_at=now - timedelta(seconds=30),
            updated_at=now - timedelta(seconds=30),
        )
        session.add_all([portfolio, campaign, order])
        session.commit()

        result = broker.process_pending_orders(session, portfolio, allowed_sides={"BUY"})
        session.commit()
        assert result["filled"] == 0
        assert session.get(BrokerOrder, order.id).status == "REJECTED"
        assert session.get(Portfolio, portfolio.id).cash == 1_000_000
        assert session.query(OrderFill).count() == 0
    finally:
        session.close()


def test_newer_untrusted_snapshot_cannot_fill_pending_exit():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    broker = PaperBrokerService()
    now = datetime.now(timezone.utc)
    try:
        portfolio = Portfolio(
            id="port_untrusted", name="test", mode="paper", cash=90_000,
            initial_cash=100_000, realized_pnl=0, kill_switch_active=False,
        )
        instrument = Instrument(
            id="inst_untrusted", source_instrument_code="789", isin="IRO1TEST0003",
            ticker="خودرو", ticker_normalized="خودرو", name_fa="ایران خودرو",
            market="TSE", board="main", base_volume=1, is_active=True,
        )
        position = Position(
            id="pos_untrusted", portfolio_id=portfolio.id, symbol="خودرو", quantity=100,
            average_entry_price=100, current_price=100, total_invested_rials=10_000,
            opened_at=now - timedelta(days=1), is_open=True,
        )
        session.add_all([portfolio, instrument, position])
        session.commit()
        order, _ = broker.create_exit_order(portfolio, position.id, current_price=100, ratio=1.0)
        order.created_at = now - timedelta(seconds=20)
        order.updated_at = order.created_at
        prior_batch, prior = _official_snapshot(
            instrument.id, order.created_at - timedelta(seconds=1),
            price=100, volume=1_000_000, suffix="untrusted_prior",
        )
        poisoned = MarketSnapshot(
            instrument_id=instrument.id,
            source_timestamp=now - timedelta(seconds=5),
            last_price=120, close_price=120, high_price=120, low_price=120,
            yesterday_price=100, volume=2_000_000, value=240_000_000,
            trade_count=1000, allowed_min=95, allowed_max=125, state="OPEN",
            available_at=now, ingested_at=now,
            source_key="brsapi_market_reference", trust_tier="REFERENCE",
            trade_eligible=False,
        )
        session.add_all([order, prior_batch, prior, poisoned])
        session.commit()

        result = broker.process_pending_orders(session, portfolio)
        session.commit()

        assert result["filled"] == 0
        assert session.query(BrokerOrder).filter_by(id=order.id).one().status == "SUBMITTED"
        assert session.query(OrderFill).count() == 0
        assert session.query(Position).filter_by(id=position.id).one().is_open is True
    finally:
        session.close()


def test_pending_exit_advances_past_no_volume_snapshot_and_fills_later_crossing():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    broker = PaperBrokerService()
    now = datetime.now(timezone.utc)
    try:
        portfolio = Portfolio(
            id="port_cursor", name="test", mode="paper", cash=90_000,
            initial_cash=100_000, realized_pnl=0, kill_switch_active=False,
        )
        instrument = Instrument(
            id="inst_cursor", source_instrument_code="991", isin="IRO1TEST0991",
            ticker="کرسر", ticker_normalized="کرسر", name_fa="کرسر",
            market="TSE", board="main", base_volume=1, is_active=True,
        )
        position = Position(
            id="pos_cursor", portfolio_id=portfolio.id, symbol="کرسر", quantity=100,
            average_entry_price=100, current_price=100, total_invested_rials=10_000,
            opened_at=now - timedelta(days=1), is_open=True,
        )
        trade_log = PaperTradeLog(
            portfolio_id=portfolio.id, symbol="کرسر", side="BUY", entry_price=100,
            quantity=100, total_invested_rials=10_000,
            entry_at=now - timedelta(days=1), reason_fa="test", is_closed=False,
        )
        session.add_all([portfolio, instrument, position, trade_log])
        session.commit()
        order, _ = broker.create_exit_order(portfolio, position.id, current_price=100, ratio=1.0)
        order.created_at = now - timedelta(seconds=30)
        order.updated_at = order.created_at
        prior_batch, prior = _official_snapshot(
            instrument.id, order.created_at - timedelta(seconds=1),
            price=99, volume=1_000, suffix="cursor_prior",
        )
        no_volume_batch, no_volume = _official_snapshot(
            instrument.id, order.created_at + timedelta(seconds=5),
            price=100, volume=1_000, suffix="cursor_no_volume",
        )
        later_batch, later = _official_snapshot(
            instrument.id, order.created_at + timedelta(seconds=10),
            price=110, volume=1_001_000, suffix="cursor_later",
        )
        session.add_all([
            order, prior_batch, prior, no_volume_batch, no_volume, later_batch, later,
        ])
        session.commit()

        first = broker.process_pending_orders(session, portfolio)
        session.commit()
        assert first["filled"] == 0
        refreshed = session.query(BrokerOrder).filter_by(id=order.id).one()
        assert refreshed.last_evaluated_snapshot_at == no_volume.source_timestamp

        second = broker.process_pending_orders(session, portfolio)
        session.commit()
        assert second["filled"] == 1
        assert session.query(OrderFill).filter_by(order_id=order.id).count() == 1
        assert session.query(BrokerOrder).filter_by(id=order.id).one().status == "FILLED"
    finally:
        session.close()
