"""Evidence-based liveness, data provenance, and fail-closed health routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from packages.domain.models import DataSourceReceipt, Instrument
from packages.shared.config import settings
from packages.shared.database import get_sync_db
from packages.shared.datetime_utils import now_utc, to_utc_iso
from services.collector.quality import evaluate_data_gate
from services.collector.service import IngestionCoordinator
from packages.data_adapters.source_registry import load_source_registry


router = APIRouter(tags=["Health & Telemetry"])


@router.get("/health")
def liveness_check():
    """Process liveness only; this endpoint makes no data-quality claim."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "trading_mode": settings.trading_mode,
        "live_guard": "LOCKED" if not settings.live_trading_enabled else "ARMED",
    }


def _receipt_item(receipt: DataSourceReceipt | None, *, source_key: str, name_fa: str, kind: str) -> dict:
    if receipt is None:
        return {
            "source_key": source_key,
            "source_kind": kind,
            "name_fa": name_fa,
            "status": "UNAVAILABLE",
            "mode": "reference_only" if kind == "market_reference" else "official",
            "record_count": 0,
            "last_attempt": None,
            "last_success": None,
            "schema_version": "unverified",
            "error": "هیچ receipt معتبری برای این منبع ثبت نشده است.",
        }
    return {
        "source_key": receipt.source_key,
        "source_kind": receipt.source_kind,
        "name_fa": name_fa,
        "status": receipt.status,
        "mode": receipt.mode,
        "record_count": receipt.record_count,
        "last_attempt": receipt.last_attempt_at.isoformat() if receipt.last_attempt_at else None,
        "last_success": receipt.last_success_at.isoformat() if receipt.last_success_at else None,
        "schema_version": receipt.schema_version,
        "error": receipt.error_message,
        "metadata": receipt.metadata_json or {},
    }


@router.get("/data/health")
def data_health_status(db: Session = Depends(get_sync_db)):
    """Report only measured provider receipts and the exact paper-trade gate."""
    receipts = {r.source_key: r for r in db.query(DataSourceReceipt).all()}
    gate = evaluate_data_gate(db, require_market_open=False)
    symbol_count = db.query(Instrument).filter(Instrument.is_active == True).count()
    sources = [
        _receipt_item(receipts.get("tsetmc_market_watch"), source_key="tsetmc_market_watch", name_fa="دیده‌بان لحظه‌ای رسمی TSETMC", kind="market"),
        _receipt_item(receipts.get("tsetmc_eod"), source_key="tsetmc_eod", name_fa="تاریخچه قیمت رسمی TSETMC", kind="market"),
        _receipt_item(receipts.get("codal_disclosures"), source_key="codal_disclosures", name_fa="اطلاعیه‌های رسمی کدال/سدرا", kind="fundamental"),
        _receipt_item(receipts.get("issuer_financials"), source_key="issuer_financials", name_fa="صورت‌های مالی و نسبت‌های ناشر", kind="fundamental"),
    ]
    return {
        "overall_status": gate.status,
        "overall_status_fa": "منابع لازم معتبر و تازه‌اند؛ گیت داده آماده است." if gate.allowed else "معامله به‌دلیل نبود شواهد کافی از داده معتبر متوقف است.",
        "provider_mode": settings.market_data_mode,
        "active_symbol_count": symbol_count,
        "sources": sources,
        "trade_gate": gate.to_dict(),
        "system_time_utc": to_utc_iso(now_utc()),
    }


@router.get("/data/providers")
def data_provider_catalog():
    """Return the audited provider catalog; never return tokens or passwords."""
    return load_source_registry()


@router.post("/data/backfill")
async def trigger_data_backfill(db: Session = Depends(get_sync_db)):
    """Refresh the direct CDN feed, then advance the resumable CDN history job."""
    coord = IngestionCoordinator(db)
    try:
        live = await coord.sync_live_cycle()
        from services.collector.backfill_worker import run_backfill_batch
        history = await run_backfill_batch(max_symbols=4)
        signals = coord.run_radar_scan()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "status": "COMPLETED",
        "provider_mode": settings.market_data_mode,
        "live": live,
        "history": history,
        "published_signals": len(signals),
        "message": "همگام‌سازی رسمی و محاسبه رادار تکمیل شد.",
    }
