from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.routes.opportunities import _signal_matches_fresh_instrument_snapshot, list_opportunities
from apps.api.routes.paper import _fresh_trusted_instrument_snapshot, _require_fresh_instrument_snapshot
from packages.domain.models import DataSourceReceipt, Instrument, MarketDataBatch, MarketSnapshot, PublishedSignal
from packages.shared.database import Base
from packages.shared.datetime_utils import now_utc


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _instrument(code: str) -> Instrument:
    return Instrument(
        source_instrument_code=code,
        isin=f"IR{code:0>10}",
        ticker=code,
        ticker_normalized=code,
        name_fa=code,
        is_active=True,
    )


def _snapshot(instrument_id: str, timestamp) -> MarketSnapshot:
    return MarketSnapshot(
        instrument_id=instrument_id,
        source_timestamp=timestamp,
        last_price=10_000,
        close_price=10_000,
        high_price=10_100,
        low_price=9_900,
        yesterday_price=9_950,
        volume=1_000_000,
        value=10_000_000_000,
        trade_count=100,
        allowed_min=9_500,
        allowed_max=10_500,
        state="ACTIVE",
    )


def _signal(instrument: Instrument, as_of, expires_at) -> PublishedSignal:
    return PublishedSignal(
        id=f"sig-{instrument.ticker}",
        instrument_id=instrument.id,
        symbol=instrument.ticker,
        name_fa=instrument.name_fa,
        as_of=as_of,
        actionable=True,
        opportunity_score=80,
        p_profit=0.7,
        confidence=80,
        signal_strength=80,
        current_price=10_000,
        entry_zone={"low": 9_900, "high": 10_100},
        invalidation={"price": 9_500},
        exit_plan={"targets": [11_000]},
        strategy_votes=[],
        top_reasons_fa=[],
        risk_flags_fa=[],
        expires_at=expires_at,
    )


def test_signal_requires_non_null_expiry_and_fresh_snapshot_of_its_own_symbol():
    db = _session()
    target = _instrument("TARGET")
    other = _instrument("OTHER")
    db.add_all([target, other])
    db.flush()
    now = now_utc()
    stale_at = now - timedelta(days=1)
    db.add_all([
        _snapshot(target.id, stale_at),
        _snapshot(other.id, now - timedelta(seconds=1)),
    ])
    stale_signal = _signal(target, stale_at, now + timedelta(minutes=5))
    null_expiry_signal = _signal(other, now - timedelta(seconds=1), None)
    null_expiry_signal.id = "sig-null-expiry"
    db.add_all([stale_signal, null_expiry_signal])
    db.commit()

    assert _signal_matches_fresh_instrument_snapshot(db, stale_signal) is False
    assert _signal_matches_fresh_instrument_snapshot(db, null_expiry_signal) is False


def test_trade_snapshot_guard_rejects_stale_target_even_if_other_symbols_are_fresh():
    now = now_utc()
    stale = _snapshot("target", now - timedelta(days=1))
    with pytest.raises(HTTPException) as blocked:
        _require_fresh_instrument_snapshot(stale)
    assert blocked.value.status_code == 409

    fresh = _snapshot("target", now - timedelta(seconds=1))
    assert _require_fresh_instrument_snapshot(fresh) == fresh.source_timestamp


def test_manual_trade_snapshot_guard_ignores_newer_untrusted_row():
    db = _session()
    instrument = _instrument("TRUSTED")
    db.add(instrument)
    official_batch = MarketDataBatch(
        source_key="tsetmc_cdn_market_watch", provider_name="official",
        source_timestamp=now_utc(), mode="official", trust_tier="OFFICIAL_DIRECT",
        trade_eligible=True, schema_version="tsetmc-cdn-market-watch-v1",
        row_count=1, complete=True,
    )
    bad_batch = MarketDataBatch(
        source_key="tsetmc_cdn_market_watch", provider_name="bad",
        source_timestamp=now_utc(), mode="official", trust_tier="OFFICIAL_DIRECT",
        trade_eligible=True, schema_version="legacy-v1", row_count=1, complete=False,
    )
    db.add_all([official_batch, bad_batch])
    db.flush()
    trusted = _snapshot(instrument.id, now_utc() - timedelta(seconds=2))
    trusted.source_key = "tsetmc_cdn_market_watch"
    trusted.batch_id = official_batch.id
    trusted.trust_tier = "OFFICIAL_DIRECT"
    trusted.trade_eligible = True
    poison = _snapshot(instrument.id, now_utc() - timedelta(seconds=1))
    poison.last_price = 1
    poison.source_key = "tsetmc_cdn_market_watch"
    poison.batch_id = bad_batch.id
    poison.trust_tier = "OFFICIAL_DIRECT"
    poison.trade_eligible = True
    db.add_all([trusted, poison])
    db.commit()

    selected = _fresh_trusted_instrument_snapshot(db, instrument.id)
    assert selected.id == trusted.id
    assert selected.last_price == 10_000


def test_recent_official_research_remains_visible_when_current_receipt_is_down():
    db = _session()
    instrument = _instrument("RESEARCH")
    db.add(instrument)
    batch = MarketDataBatch(
        source_key="tsetmc_cdn_market_watch", provider_name="official",
        source_timestamp=now_utc(), mode="official", trust_tier="OFFICIAL_DIRECT",
        trade_eligible=True, schema_version="tsetmc-cdn-market-watch-v1",
        row_count=1, complete=True,
    )
    db.add(batch)
    db.flush()
    snapshot = _snapshot(instrument.id, now_utc() - timedelta(minutes=5))
    snapshot.source_key = "tsetmc_cdn_market_watch"
    snapshot.batch_id = batch.id
    snapshot.trust_tier = "OFFICIAL_DIRECT"
    snapshot.trade_eligible = True
    signal = _signal(
        instrument,
        snapshot.source_timestamp,
        now_utc() + timedelta(hours=1),
    )
    signal.actionable = False
    db.add_all([
        snapshot,
        signal,
        DataSourceReceipt(
            source_key="tsetmc_market_watch", source_kind="market",
            provider_name="official", mode="official", status="UNAVAILABLE",
        ),
    ])
    db.commit()

    research = list_opportunities(
        horizon=None, grade=None, min_score=0, actionable_only=False, sector=None, db=db,
    )
    actionable = list_opportunities(
        horizon=None, grade=None, min_score=0, actionable_only=True, sector=None, db=db,
    )
    assert [item.id for item in research] == [signal.id]
    assert actionable == []
