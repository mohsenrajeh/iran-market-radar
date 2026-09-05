"""Shared provenance-bound queries for every paper decision and fill."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from packages.domain.models import (
    ClientTypeSnapshot, EODBar, MarketDataBatch, MarketSnapshot,
)
from packages.shared.datetime_utils import now_utc


def trusted_market_snapshot_base_query(db: Session):
    return (
        db.query(MarketSnapshot)
        .join(MarketDataBatch, MarketDataBatch.id == MarketSnapshot.batch_id)
        .filter(
            MarketSnapshot.source_key == "tsetmc_cdn_market_watch",
            MarketSnapshot.trade_eligible == True,
            MarketSnapshot.trust_tier == "OFFICIAL_DIRECT",
            MarketSnapshot.batch_id.isnot(None),
            MarketDataBatch.source_key == "tsetmc_cdn_market_watch",
            MarketDataBatch.schema_version == "tsetmc-cdn-market-watch-v1",
            MarketDataBatch.complete == True,
            MarketDataBatch.trade_eligible == True,
            MarketDataBatch.trust_tier == "OFFICIAL_DIRECT",
        )
    )


def trusted_market_snapshot_query(db: Session, instrument_id: str):
    return trusted_market_snapshot_base_query(db).filter(
        MarketSnapshot.instrument_id == instrument_id
    )


def latest_trusted_market_snapshot(
    db: Session,
    instrument_id: str,
    *,
    after: datetime | None = None,
    max_age_seconds: int | None = None,
):
    query = trusted_market_snapshot_query(db, instrument_id)
    if max_age_seconds is not None:
        query = query.filter(
            MarketSnapshot.source_timestamp >= now_utc() - timedelta(seconds=max_age_seconds)
        )
    if after is not None:
        query = query.filter(MarketSnapshot.source_timestamp > after)
        snapshot = query.order_by(MarketSnapshot.source_timestamp.asc()).first()
    else:
        snapshot = query.order_by(MarketSnapshot.source_timestamp.desc()).first()
    if snapshot is None or max_age_seconds is None:
        return snapshot
    source_at = snapshot.source_timestamp
    if source_at.tzinfo is None:
        source_at = source_at.replace(tzinfo=timezone.utc)
    age = (now_utc() - source_at.astimezone(timezone.utc)).total_seconds()
    return snapshot if 0 <= age <= max_age_seconds else None


def trusted_eod_base_query(db: Session):
    return (
        db.query(EODBar)
        .join(MarketDataBatch, MarketDataBatch.id == EODBar.batch_id)
        .filter(
            EODBar.source_key == "tsetmc_cdn_history",
            EODBar.trade_eligible == True,
            EODBar.trust_tier == "OFFICIAL_DIRECT",
            EODBar.batch_id.isnot(None),
            MarketDataBatch.source_key == "tsetmc_cdn_history",
            MarketDataBatch.schema_version == "tsetmc-cdn-history-v1",
            MarketDataBatch.complete == True,
            MarketDataBatch.trade_eligible == True,
            MarketDataBatch.trust_tier == "OFFICIAL_DIRECT",
        )
    )


def trusted_eod_query(db: Session, instrument_id: str):
    return trusted_eod_base_query(db).filter(EODBar.instrument_id == instrument_id)


def trusted_client_type_base_query(db: Session):
    return (
        db.query(ClientTypeSnapshot)
        .join(MarketDataBatch, MarketDataBatch.id == ClientTypeSnapshot.batch_id)
        .filter(
            ClientTypeSnapshot.source_key == "tsetmc_cdn_history",
            ClientTypeSnapshot.trade_eligible == True,
            ClientTypeSnapshot.trust_tier == "OFFICIAL_DIRECT",
            ClientTypeSnapshot.batch_id.isnot(None),
            MarketDataBatch.source_key == "tsetmc_cdn_history",
            MarketDataBatch.schema_version == "tsetmc-cdn-history-v1",
            MarketDataBatch.complete == True,
            MarketDataBatch.trade_eligible == True,
            MarketDataBatch.trust_tier == "OFFICIAL_DIRECT",
        )
    )


def trusted_client_type_query(db: Session, instrument_id: str):
    return trusted_client_type_base_query(db).filter(
        ClientTypeSnapshot.instrument_id == instrument_id
    )
