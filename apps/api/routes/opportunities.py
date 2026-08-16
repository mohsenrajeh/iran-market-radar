"""Opportunities radar routes."""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from packages.domain.models import PublishedSignal
from packages.domain.schemas import PublishedSignalSchema
from packages.shared.database import get_sync_db

router = APIRouter(prefix="/opportunities", tags=["Opportunities Radar"])


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
    query = db.query(PublishedSignal).filter(PublishedSignal.opportunity_score >= min_score)

    if actionable_only:
        query = query.filter(PublishedSignal.actionable == True)
    if horizon:
        query = query.filter(PublishedSignal.horizon == horizon)
    if grade:
        query = query.filter(PublishedSignal.grade == grade)
    if sector:
        query = query.filter(PublishedSignal.sector == sector)

    signals = query.order_by(PublishedSignal.opportunity_score.desc()).all()
    return signals


@router.get("/{signal_id}", response_model=PublishedSignalSchema)
def get_opportunity_detail(signal_id: str, db: Session = Depends(get_sync_db)):
    """Returns complete quantitative evidence, strategy votes, and execution plan for a signal."""
    sig = db.query(PublishedSignal).filter(PublishedSignal.id == signal_id).first()
    if not sig:
        raise HTTPException(status_code=404, detail="سیگنال مورد نظر یافت نشد.")
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
