from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.domain.models import DataSourceReceipt, EODBar, Instrument, MarketDataBatch, MarketSnapshot
from packages.shared.database import Base
from services.collector.trusted_queries import trusted_eod_base_query


def test_reference_mapping_cannot_substitute_same_price_wrong_official_identity():
    from services.collector.backfill_worker import _identity_matches

    instrument = Instrument(
        id="victim", source_instrument_code="IRO100000001", isin="IRO100000001",
        ticker="هدف", ticker_normalized="هدف", name_fa="شرکت هدف", is_active=True,
    )
    attacker_identity = {
        "ins_code": "999", "isin": "IRO100000099", "ticker": "بدل",
        "ticker_normalized": "بدل", "name_fa": "شرکت بدل",
    }
    assert _identity_matches(instrument, "999", attacker_identity) is False


def test_empty_or_failed_eod_response_is_retryable_not_terminally_excluded():
    from services.collector.backfill_worker import _short_history_terminal_details

    assert _short_history_terminal_details([], {"eod": "timeout", "client": None}, 260) is None
    assert _short_history_terminal_details([], {"eod": None, "client": None}, 260) is None
    details = _short_history_terminal_details([{"trading_date": "2026-08-16"}] * 250, None, 260)
    assert details is not None
    assert details["eod_rows"] == 250
    assert details["eligible_after"]


def test_legacy_or_wrong_schema_history_batch_is_never_trusted():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        instrument = Instrument(
            id="legacy-history", source_instrument_code="123", isin="IRO100000123",
            ticker="قدیمی", ticker_normalized="قدیمی", name_fa="قدیمی", is_active=True,
        )
        batch = MarketDataBatch(
            id="wrong-history-schema", source_key="tsetmc_cdn_history", provider_name="TSETMC",
            source_timestamp=datetime.now(timezone.utc), mode="official",
            trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
            schema_version="legacy-unverified-v0", row_count=1, complete=True,
        )
        bar = EODBar(
            instrument_id=instrument.id, trading_date=date(2026, 8, 16),
            open=100, high=101, low=99, close=100, last=100, yesterday_price=100,
            volume=1000, value=100000, trade_count=10,
            source_key="tsetmc_cdn_history", batch_id=batch.id,
            trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
        )
        db.add_all([instrument, batch, bar])
        db.commit()
        assert trusted_eod_base_query(db).count() == 0
    finally:
        db.close()


def test_backfill_progress_receipt_refreshes_even_without_a_new_remote_batch():
    from services.collector.backfill_worker import _persist_history_progress

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        instrument = Instrument(
            id="ready-history", source_instrument_code="456", isin="IRO100000456",
            ticker="آماده", ticker_normalized="آماده", name_fa="آماده", is_active=True,
        )
        batch = MarketDataBatch(
            id="valid-history-schema", source_key="tsetmc_cdn_history", provider_name="TSETMC",
            source_timestamp=datetime.now(timezone.utc), mode="official",
            trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
            schema_version="tsetmc-cdn-history-v1", row_count=1, complete=True,
        )
        bar = EODBar(
            instrument_id=instrument.id, trading_date=date(2026, 8, 16),
            open=100, high=101, low=99, close=100, last=100, yesterday_price=100,
            volume=1000, value=100000, trade_count=10,
            source_key="tsetmc_cdn_history", batch_id=batch.id,
            trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
        )
        stale_receipt = DataSourceReceipt(
            source_key="tsetmc_eod", source_kind="market", provider_name="TSETMC",
            status="DEGRADED", mode="official", record_count=0,
            metadata_json={"symbols_ready": 0},
        )
        db.add_all([instrument, batch, bar, stale_receipt])
        db.commit()

        _, ready, expected = _persist_history_progress(
            db, stale_receipt, required=1, completed=0, rejected=0,
            rejected_until={}, terminal_ineligible={},
        )
        db.refresh(stale_receipt)
        assert (ready, expected) == (1, 1)
        assert stale_receipt.status == "HEALTHY"
        assert stale_receipt.record_count == 1
        assert stale_receipt.metadata_json["symbols_ready"] == 1
    finally:
        db.close()


def test_cdn_backfill_requires_bridge_match_and_persists_bound_history(monkeypatch, tmp_path):
    db_path = tmp_path / "backfill.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    now = datetime(2026, 8, 17, 9, 30, tzinfo=timezone.utc)
    inst = Instrument(
        id="official_1", source_instrument_code="123456", isin="IRO100000001",
        ticker="نماد", ticker_normalized="نماد", name_fa="شرکت", is_active=True,
    )
    live_batch = MarketDataBatch(
        id="live-batch", source_key="tsetmc_cdn_market_watch", provider_name="TSE",
        source_timestamp=now, mode="official", trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
        schema_version="tsetmc-cdn-market-watch-v1", row_count=560, complete=True,
    )
    prior_receipt = DataSourceReceipt(
        source_key="tsetmc_eod", source_kind="market", provider_name="TSETMC Public CDN",
        mode="official", status="DEGRADED", schema_version="tsetmc-cdn-history-v1",
        record_count=0, metadata_json={"symbols_ready": 0},
    )
    db.add_all([inst, live_batch, prior_receipt]); db.flush()
    db.add(MarketSnapshot(
        instrument_id=inst.id, source_timestamp=now, last_price=101, close_price=101,
        high_price=102, low_price=99, yesterday_price=100, volume=1000, value=100000,
        trade_count=10, allowed_min=95, allowed_max=105, state="مجاز",
        source_key="tsetmc_cdn_market_watch", batch_id="live-batch",
        trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
    ))
    old_v1 = MarketDataBatch(
        id="old-v1-batch", source_key="tsetmc_cdn_market_watch", provider_name="TSE",
        source_timestamp=now + timedelta(minutes=1), mode="official",
        trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
        schema_version="tse-webgw-market-watch-v1", row_count=560, complete=True,
    )
    db.add(old_v1)
    db.add(MarketSnapshot(
        instrument_id=inst.id, source_timestamp=now + timedelta(minutes=1),
        last_price=999, close_price=999, high_price=999, low_price=999,
        yesterday_price=999, volume=1, value=999, trade_count=1,
        allowed_min=900, allowed_max=1050, state="مجاز",
        source_key="tsetmc_cdn_market_watch", batch_id=old_v1.id,
        trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
    ))
    db.commit()
    expected_isin = inst.isin
    expected_ticker = inst.ticker
    expected_ticker_normalized = inst.ticker_normalized
    expected_name = inst.name_fa
    db.close()

    rows = []
    clients = []
    for offset in range(260):
        day = date(2026, 8, 16) - timedelta(days=offset)
        rows.append({
            "trading_date": day.isoformat(), "open": 100, "high": 102, "low": 99,
            "close": 100, "last": 101, "yesterday_price": 100, "volume": 1000,
            "value": 100000, "trade_count": 10, "allowed_min": None, "allowed_max": None,
        })
        clients.append({
            "trading_date": day.isoformat(), "real_buy_count": 1, "real_buy_volume": 600,
            "real_buy_value": 60000, "real_sell_count": 1, "real_sell_volume": 500,
            "real_sell_value": 50000, "legal_buy_count": 1, "legal_buy_volume": 400,
            "legal_buy_value": 40000, "legal_sell_count": 1, "legal_sell_volume": 500,
            "legal_sell_value": 50000,
        })

    async def fake_pair(_):
        return rows, clients, {
            "ins_code": "123456", "isin": expected_isin,
            "ticker": expected_ticker, "ticker_normalized": expected_ticker_normalized,
            "name_fa": expected_name,
        }, None

    import services.collector.backfill_worker as worker
    monkeypatch.setattr(worker, "SyncSessionLocal", Session)
    monkeypatch.setattr(worker, "_fetch_pair", fake_pair)
    monkeypatch.setattr(worker.settings, "tsetmc_market_hours_enforced", False)
    result = __import__("asyncio").run(worker.run_backfill_batch(max_symbols=1))
    assert result["processed"] == 1
    check = Session()
    try:
        from packages.domain.models import EODBar, ClientTypeSnapshot
        assert check.query(EODBar).filter(EODBar.trade_eligible == True).count() == 260
        assert check.query(ClientTypeSnapshot).filter(ClientTypeSnapshot.trade_eligible == True).count() == 260
        bar = check.query(EODBar).first()
        assert bar.batch_id
        assert bar.trust_tier == "OFFICIAL_DIRECT"
        refreshed_receipt = check.query(DataSourceReceipt).filter_by(source_key="tsetmc_eod").one()
        assert refreshed_receipt.metadata_json["symbols_ready"] == 1
        assert refreshed_receipt.record_count == 260
    finally:
        check.close()
