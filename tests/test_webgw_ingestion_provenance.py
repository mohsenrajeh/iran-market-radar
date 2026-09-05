"""Regression coverage for the sole live provider: TSETMC public CDN."""
import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.domain.models import DataSourceReceipt, EODBar, Instrument, MarketDataBatch, MarketSnapshot
from packages.shared.database import Base
from services.collector.service import IngestionCoordinator


class _Cdn3:
    provider_name = "TSETMC Public CDN"
    base_url = "https://cdn.tsetmc.com"
    last_response_at = datetime.now(timezone.utc)
    last_failure_kind = None
    transport_clock_source = "test"
    rejected_row_count = 0
    raw_row_count = 3
    last_error = None
    row_count = 3

    def __init__(self, **_kwargs):
        pass

    async def fetch_market_rows(self):
        return [{
            "source_instrument_code": str(10_000_000_000_000 + i),
            "isin": f"IRO1{i:08d}", "ticker": f"نماد{i}",
            "ticker_normalized": f"نماد{i}", "name_fa": f"شرکت {i}",
            "market": "TSE", "open": 1000.0, "high": 1050.0, "low": 990.0,
            "last": 1020.0, "close": 1010.0, "yesterday_price": 1000.0,
            "volume": 3_600_000_000 if i == 0 else 1000,
            "value": 3_600_000_000_000.0 if i == 0 else 1_000_000.0,
            "trade_count": 100, "allowed_min": 950.0, "allowed_max": 1050.0,
            "pe": 7.0, "eps": 144.0, "market_value": 10_000_000.0,
            "state": "A", "trade_eligible": True,
            "observed_at": self.last_response_at, "source": "TSETMC_PUBLIC_CDN",
        } for i in range(self.row_count)]


class _Cdn2(_Cdn3):
    row_count = 2
    raw_row_count = 2


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_cdn_rows_are_bound_to_complete_batch_and_fixture_identity_is_not_reused(monkeypatch):
    db = _db()
    try:
        fixture = Instrument(
            id="fixture_0", source_instrument_code="INS_0", isin="IRO100000000",
            ticker="قدیمی", ticker_normalized="قدیمی", name_fa="قدیمی", is_active=True,
        )
        db.add(fixture)
        db.add(EODBar(
            instrument_id=fixture.id, trading_date=datetime(2026, 8, 16).date(),
            open=1, high=1, low=1, close=1, last=1, yesterday_price=1,
            volume=1, value=1, trade_count=1, trade_eligible=False,
        ))
        db.commit()
        monkeypatch.setattr("services.collector.service.TsetmcCdnMarketWatchAdapter", _Cdn3)
        monkeypatch.setattr("services.collector.service.settings.quality.minimum_expected_equity_universe", 3)
        monkeypatch.setattr("services.collector.service.settings.tsetmc_market_hours_enforced", False)

        result = asyncio.run(IngestionCoordinator(db).sync_cdn_market_watch())

        assert result["trade_eligible"] is True
        assert result["providers"] == ["TSETMC Public CDN"]
        batch = db.query(MarketDataBatch).one()
        assert batch.source_key == "tsetmc_cdn_market_watch"
        assert batch.schema_version == "tsetmc-cdn-market-watch-v1"
        assert batch.complete and batch.trade_eligible
        assert db.query(MarketSnapshot).filter_by(batch_id=batch.id, trade_eligible=True).count() == 3
        assert db.get(Instrument, "fixture_0").is_active is False
        official = db.query(Instrument).filter_by(isin="IRO100000000").one()
        assert official.id != "fixture_0"
        receipt = db.query(DataSourceReceipt).filter_by(source_key="tsetmc_market_watch").one()
        assert receipt.status == "HEALTHY"
    finally:
        db.close()


def test_cdn_truncated_response_is_rejected_against_previous_complete_batch(monkeypatch):
    db = _db()
    try:
        db.add(MarketDataBatch(
            source_key="tsetmc_cdn_market_watch", provider_name="TSETMC Public CDN",
            source_timestamp=datetime(2026, 8, 16, tzinfo=timezone.utc), mode="official",
            trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
            schema_version="tsetmc-cdn-market-watch-v1", row_count=3, complete=True,
        ))
        db.commit()
        monkeypatch.setattr("services.collector.service.TsetmcCdnMarketWatchAdapter", _Cdn2)
        monkeypatch.setattr("services.collector.service.settings.quality.minimum_expected_equity_universe", 2)
        monkeypatch.setattr("services.collector.service.settings.tsetmc_market_hours_enforced", False)

        with pytest.raises(RuntimeError, match="freshness/completeness"):
            asyncio.run(IngestionCoordinator(db).sync_cdn_market_watch())
        assert db.query(MarketSnapshot).count() == 0
        receipt = db.query(DataSourceReceipt).filter_by(source_key="tsetmc_market_watch").one()
        assert receipt.status == "SCHEMA_ERROR"
        assert receipt.metadata_json["universe_coverage"] == pytest.approx(2 / 3)
    finally:
        db.close()


def test_cdn_cold_start_truncation_is_rejected_by_reviewed_floor(monkeypatch):
    db = _db()
    try:
        monkeypatch.setattr("services.collector.service.TsetmcCdnMarketWatchAdapter", _Cdn2)
        monkeypatch.setattr("services.collector.service.settings.quality.minimum_expected_equity_universe", 3)
        monkeypatch.setattr("services.collector.service.settings.tsetmc_market_hours_enforced", False)
        with pytest.raises(RuntimeError, match="freshness/completeness"):
            asyncio.run(IngestionCoordinator(db).sync_cdn_market_watch())
        assert db.query(MarketSnapshot).count() == 0
    finally:
        db.close()
