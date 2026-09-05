from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.domain.models import Base, BrokerOrder, Instrument, Portfolio, PublishedSignal
from packages.shared.datetime_utils import now_utc
from services.collector.service import IngestionCoordinator


def _signal(signal_id: str, instrument_id: str) -> PublishedSignal:
    return PublishedSignal(
        id=signal_id, instrument_id=instrument_id, symbol="فولاد", name_fa="فولاد",
        market="TSE", as_of=now_utc(), actionable=False, grade="C", opportunity_score=10,
        p_profit=0.5, confidence=10, signal_strength=10, current_price=100,
        entry_zone={}, invalidation={}, exit_plan={}, liquidity_score=0,
        fill_probability_score=0, data_quality=0, regime="unknown",
        strategy_votes=[], top_reasons_fa=[], risk_flags_fa=[], decision_components={},
        model_version="none", strategy_version="none", calibration_version="none",
    )


def test_radar_scan_preserves_signal_referenced_by_pending_order(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        portfolio = Portfolio(
            id="port_signal_hold", name="test", mode="paper", cash=100_000,
            initial_cash=100_000, realized_pnl=0, kill_switch_active=False,
        )
        instrument = Instrument(
            id="inst_signal_hold", source_instrument_code="123", isin="IRO1SIGL0001",
            ticker="فولاد", ticker_normalized="فولاد", name_fa="فولاد",
            market="TSE", board="main", base_volume=1, is_active=False,
        )
        keep = _signal("sig_keep", instrument.id)
        stale = _signal("sig_stale", instrument.id)
        keep_id, stale_id = keep.id, stale.id
        pending = BrokerOrder(
            id="ord_keep", portfolio_id=portfolio.id, signal_id=keep.id,
            symbol="فولاد", side="BUY", order_type="LIMIT", price=100,
            quantity=10, filled_quantity=0, status="SUBMITTED",
        )
        db.add_all([portfolio, instrument, keep, stale, pending])
        db.commit()
        monkeypatch.setattr(
            "services.collector.service.compute_market_regime_from_db",
            lambda _db: SimpleNamespace(regime_label="neutral"),
        )

        IngestionCoordinator(db).run_radar_scan()

        assert db.get(PublishedSignal, keep_id) is not None
        assert db.get(PublishedSignal, stale_id) is None
    finally:
        db.close()
