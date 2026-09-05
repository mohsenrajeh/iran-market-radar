"""Opportunities radar routes."""
import asyncio
import json
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from packages.domain.models import PublishedSignal, DataSourceReceipt, Instrument, MarketSnapshot
from packages.domain.schemas import PublishedSignalSchema
from packages.shared.config import settings
from packages.shared.database import get_sync_db
from packages.shared.datetime_utils import now_utc
from services.collector.trusted_queries import (
    trusted_market_snapshot_base_query, trusted_market_snapshot_query,
)

router = APIRouter(prefix="/opportunities", tags=["Opportunities Radar"])


def _official_signal_feed_is_fresh(
    db: Session,
    *,
    max_age_seconds: int | None = None,
    require_current_receipt: bool = True,
) -> bool:
    if settings.market_data_mode != "official":
        return True
    receipt = db.query(DataSourceReceipt).filter(
        DataSourceReceipt.source_key == "tsetmc_market_watch"
    ).first()
    fixture_count = db.query(Instrument).filter(
        Instrument.is_active == True,
        Instrument.source_instrument_code.like("INS\\_%", escape="\\"),
    ).count()
    latest_snapshot = trusted_market_snapshot_base_query(db).order_by(
        MarketSnapshot.source_timestamp.desc()
    ).first()
    latest_market_at = latest_snapshot.source_timestamp if latest_snapshot else None
    if latest_market_at and latest_market_at.tzinfo is None:
        latest_market_at = latest_market_at.replace(tzinfo=timezone.utc)
    market_age = (
        (now_utc() - latest_market_at.astimezone(timezone.utc)).total_seconds()
        if latest_market_at else None
    )
    return bool(
        (not require_current_receipt or (
            receipt is not None
            and receipt.status == "HEALTHY"
            and receipt.mode == "official"
        ))
        and not fixture_count
        and market_age is not None
        and market_age <= (max_age_seconds or settings.quality.critical_market_stale_seconds)
    )


def _signal_matches_fresh_instrument_snapshot(
    db: Session, signal: PublishedSignal, *, max_age_seconds: int | None = None
) -> bool:
    """Bind a signal to the newest fresh snapshot of its own instrument."""
    if signal.expires_at is None:
        return False
    expiry = signal.expires_at if signal.expires_at.tzinfo else signal.expires_at.replace(tzinfo=timezone.utc)
    if expiry <= now_utc():
        return False
    snapshot = (
        trusted_market_snapshot_query(db, signal.instrument_id)
        .order_by(MarketSnapshot.source_timestamp.desc())
        .first()
    )
    if snapshot is None:
        return False
    snapshot_as_of = snapshot.source_timestamp
    if snapshot_as_of.tzinfo is None:
        snapshot_as_of = snapshot_as_of.replace(tzinfo=timezone.utc)
    snapshot_age = (now_utc() - snapshot_as_of.astimezone(timezone.utc)).total_seconds()
    if snapshot_age < 0 or snapshot_age > (max_age_seconds or settings.quality.critical_market_stale_seconds):
        return False
    signal_as_of = signal.as_of if signal.as_of.tzinfo else signal.as_of.replace(tzinfo=timezone.utc)
    return snapshot_as_of <= signal_as_of <= now_utc()


@router.get("", response_model=list[PublishedSignalSchema])
def list_opportunities(
    horizon: str | None = Query(None, description="Time horizon (e.g. 5d, 10d)"),
    grade: str | None = Query(None, description="Grade filter (A+, A, B, C)"),
    min_score: float = Query(60.0, description="Minimum opportunity score"),
    actionable_only: bool = Query(True, description="Filter only actionable opportunities"),
    sector: str | None = Query(None, description="Sector name filter"),
    db: Session = Depends(get_sync_db),
):
    """
    Returns ranked and calibrated market opportunities.
    """
    max_age_seconds = settings.quality.critical_market_stale_seconds if actionable_only else 24 * 60 * 60
    if not _official_signal_feed_is_fresh(
        db,
        max_age_seconds=max_age_seconds,
        require_current_receipt=actionable_only,
    ):
        return []
    query = db.query(PublishedSignal).filter(
        PublishedSignal.opportunity_score >= min_score,
        PublishedSignal.expires_at.is_not(None),
        PublishedSignal.expires_at > now_utc(),
    )

    if actionable_only:
        query = query.filter(PublishedSignal.actionable == True)
    if horizon:
        query = query.filter(PublishedSignal.horizon == horizon)
    if grade:
        query = query.filter(PublishedSignal.grade == grade)
    if sector:
        query = query.filter(PublishedSignal.sector == sector)

    signals = query.order_by(PublishedSignal.opportunity_score.desc()).all()
    return [
        signal for signal in signals
        if _signal_matches_fresh_instrument_snapshot(db, signal, max_age_seconds=max_age_seconds)
    ]


@router.get("/{signal_id}", response_model=PublishedSignalSchema)
def get_opportunity_detail(signal_id: str, db: Session = Depends(get_sync_db)):
    """Returns complete quantitative evidence, strategy votes, and execution plan for a signal."""
    sig = db.query(PublishedSignal).filter(PublishedSignal.id == signal_id).first()
    if not sig:
        raise HTTPException(status_code=404, detail="سیگنال مورد نظر یافت نشد.")
    max_age_seconds = settings.quality.critical_market_stale_seconds if sig.actionable else 24 * 60 * 60
    if not _official_signal_feed_is_fresh(
        db,
        max_age_seconds=max_age_seconds,
        require_current_receipt=sig.actionable,
    ):
        raise HTTPException(status_code=409, detail="خوراک رسمی برای این نوع سیگنال تازه نیست.")
    if not _signal_matches_fresh_instrument_snapshot(db, sig, max_age_seconds=max_age_seconds):
        raise HTTPException(
            status_code=409,
            detail="سیگنال به snapshot رسمی و تازه همان نماد تعلق ندارد؛ اسکن دوباره لازم است.",
        )
    return sig


@router.get("/stream/sse")
async def stream_opportunities_sse():
    """Server-Sent Events (SSE) stream for real-time opportunity alerts."""
    async def event_generator():
        while True:
            # Emit heartbeat / opportunity ping
            payload = {
                "event": "HEARTBEAT",
                "timestamp": asyncio.get_event_loop().time(),
                "status": "LIVE_MONITORING",
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
