from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.domain.models import EODBar, Instrument, MarketDataBatch, MarketSnapshot
from packages.feature_engine.regime import compute_market_regime_from_db
from packages.shared.database import Base


def _batch(source_key: str, schema: str, *, complete: bool = True) -> MarketDataBatch:
    return MarketDataBatch(
        source_key=source_key,
        provider_name=source_key,
        source_timestamp=datetime.now(timezone.utc),
        mode="official",
        trust_tier="OFFICIAL_DIRECT",
        trade_eligible=True,
        schema_version=schema,
        row_count=20,
        complete=complete,
    )


def test_regime_ignores_newer_rows_from_incomplete_or_wrong_schema_batches():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        instrument = Instrument(
            source_instrument_code="123456789",
            isin="IRO1TEST00001",
            ticker="آزمون",
            ticker_normalized="آزمون",
            name_fa="آزمون",
            is_active=True,
        )
        market_batch = _batch("tsetmc_cdn_market_watch", "tsetmc-cdn-market-watch-v1")
        history_batch = _batch("tsetmc_cdn_history", "tsetmc-cdn-history-v1")
        db.add_all([instrument, market_batch, history_batch])
        db.flush()
        start = date(2026, 7, 20)
        for index in range(20):
            close = 1000.0 + index * 10
            db.add(EODBar(
                instrument_id=instrument.id,
                trading_date=start + timedelta(days=index),
                open=close,
                high=close + 5,
                low=close - 5,
                close=close,
                last=close,
                yesterday_price=close - 10,
                volume=1000,
                value=close * 1000,
                trade_count=10,
                source_key="tsetmc_cdn_history",
                batch_id=history_batch.id,
                trust_tier="OFFICIAL_DIRECT",
                trade_eligible=True,
            ))
        observed = datetime.now(timezone.utc) - timedelta(seconds=10)
        db.add(MarketSnapshot(
            instrument_id=instrument.id,
            source_timestamp=observed,
            last_price=1210,
            close_price=1210,
            high_price=1220,
            low_price=1190,
            yesterday_price=1200,
            volume=5000,
            value=6_000_000,
            trade_count=50,
            allowed_min=1140,
            allowed_max=1260,
            state="ACTIVE",
            source_key="tsetmc_cdn_market_watch",
            batch_id=market_batch.id,
            trust_tier="OFFICIAL_DIRECT",
            trade_eligible=True,
        ))
        db.commit()
        baseline = compute_market_regime_from_db(db)
        assert baseline is not None

        bad_batch = _batch("tsetmc_cdn_market_watch", "legacy-v1", complete=False)
        db.add(bad_batch)
        db.flush()
        db.add(MarketSnapshot(
            instrument_id=instrument.id,
            source_timestamp=observed + timedelta(seconds=5),
            last_price=100,
            close_price=100,
            high_price=100,
            low_price=100,
            yesterday_price=1000,
            volume=9_999_999,
            value=9_999_999_999,
            trade_count=999,
            allowed_min=90,
            allowed_max=110,
            state="ACTIVE",
            source_key="tsetmc_cdn_market_watch",
            batch_id=bad_batch.id,
            trust_tier="OFFICIAL_DIRECT",
            trade_eligible=True,
        ))
        db.commit()

        after_poison = compute_market_regime_from_db(db)
        assert after_poison == baseline
    finally:
        db.close()

def test_regime_rejects_stale_official_v2_snapshot_universe():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        instrument = Instrument(
            source_instrument_code="987654321", isin="IRO1STALE001",
            ticker="قدیمی", ticker_normalized="قدیمی", name_fa="قدیمی", is_active=True,
        )
        market_batch = _batch("tsetmc_cdn_market_watch", "tsetmc-cdn-market-watch-v1")
        history_batch = _batch("tsetmc_cdn_history", "tsetmc-cdn-history-v1")
        db.add_all([instrument, market_batch, history_batch])
        db.flush()
        start = date(2026, 7, 20)
        for index in range(20):
            close = 1000 + index
            db.add(EODBar(
                instrument_id=instrument.id, trading_date=start + timedelta(days=index),
                open=close, high=close + 1, low=close - 1, close=close, last=close,
                yesterday_price=close - 1, volume=1000, value=1_000_000,
                trade_count=10, source_key="tsetmc_cdn_history", batch_id=history_batch.id,
                trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
            ))
        stale_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.add(MarketSnapshot(
            instrument_id=instrument.id, source_timestamp=stale_at,
            last_price=1020, close_price=1020, high_price=1021, low_price=1019,
            yesterday_price=1010, volume=1000, value=1_020_000, trade_count=10,
            allowed_min=950, allowed_max=1050, state="ACTIVE",
            source_key="tsetmc_cdn_market_watch", batch_id=market_batch.id,
            trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
        ))
        db.commit()
        assert compute_market_regime_from_db(db) is None
    finally:
        db.close()
