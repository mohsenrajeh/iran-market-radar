"""Market Overview and Sector Scorecard routes."""
import asyncio
from datetime import datetime, timezone
from sqlalchemy import func
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.domain.models import (
    ClientTypeSnapshot, EODBar, Instrument, MarketSnapshot, Sector,
    PublishedSignal, DataSourceReceipt, MarketIndexSnapshot,
    MarketDataBatch, ReferenceMarketObservation,
)
from packages.domain.schemas import MarketOverviewResponse, MarketIndexSummary, SectorScorecard
from packages.shared.database import get_sync_db
from packages.shared.config import settings
from packages.shared.datetime_utils import now_utc, to_jalali_str, to_utc_iso
from packages.market_rules.trading_hours import get_market_session_state
from services.collector.trusted_queries import trusted_market_snapshot_base_query

router = APIRouter(prefix="/market", tags=["Market Overview"])


@router.get("/reference-symbols")
def get_reference_symbols(
    q: str | None = Query(None, max_length=80),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=2000),
    db: Session = Depends(get_sync_db),
):
    """Return the freshest complete normalized backup batch for viewing only.

    This endpoint intentionally has no order/signal identifiers and declares
    its non-tradable provenance in every response.
    """
    session = get_market_session_state()
    batches = (
        db.query(MarketDataBatch)
        .filter(
            MarketDataBatch.complete == True,
            MarketDataBatch.source_key == "tsetmc_cdn_market_watch",
            MarketDataBatch.id.in_(
                db.query(ReferenceMarketObservation.batch_id).distinct()
            ),
        )
        .order_by(MarketDataBatch.source_timestamp.desc().nullslast(), MarketDataBatch.received_at.desc())
        .all()
    )
    def batch_age_seconds(item: MarketDataBatch) -> int:
        source_at = item.source_timestamp or item.received_at
        if source_at.tzinfo is None:
            source_at = source_at.replace(tzinfo=timezone.utc)
        return max(0, int((now_utc() - source_at.astimezone(timezone.utc)).total_seconds()))

    batch = batches[0] if batches else None
    if batch is not None:
        query = db.query(ReferenceMarketObservation).filter(
            ReferenceMarketObservation.batch_id == batch.id
        )
        needle = (q or "").strip()
        if needle:
            query = query.filter(
                (ReferenceMarketObservation.ticker.contains(needle))
                | (ReferenceMarketObservation.name_fa.contains(needle))
            )
        total_filtered = query.count()
        observations = (
            query.order_by(ReferenceMarketObservation.ticker.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        source_at = batch.source_timestamp or batch.received_at
        if source_at.tzinfo is None:
            source_at = source_at.replace(tzinfo=timezone.utc)
        age_seconds = max(0, int((now_utc() - source_at.astimezone(timezone.utc)).total_seconds()))
        rows = [{
            "slug": item.isin or item.source_instrument_code or item.ticker,
            "ticker": item.ticker,
            "name_fa": item.name_fa,
            "last_price_rials": item.last_price,
            "closing_price_rials": item.close_price,
            "change_pct": (
                round(((item.last_price / item.yesterday_price) - 1.0) * 100.0, 2)
                if item.last_price and item.yesterday_price else None
            ),
            "volume": item.volume,
            "value_rials": item.value,
            "market_cap_rials": item.market_cap,
            "pe": item.pe,
            "source_updated_at": to_utc_iso(item.source_timestamp),
            "source_provider": batch.provider_name,
            "market": item.market,
            "allowed_min_rials": item.allowed_min,
            "allowed_max_rials": item.allowed_max,
            "state": item.state,
        } for item in observations]
        display_state = (
            "LAST_CLOSE"
            if not session["is_open"]
            else ("STALE" if age_seconds > settings.quality.critical_market_stale_seconds else "LIVE")
        )
        currently_trade_eligible = bool(
            batch.trade_eligible
            and session["is_open"]
            and age_seconds <= settings.quality.critical_market_stale_seconds
        )
        return {
            "provider": batch.provider_name,
            "mode": batch.mode.upper(),
            "trade_eligible": currently_trade_eligible,
            "rows": rows,
            "meta": {
                "page": page,
                "per_page": per_page,
                "filtered": total_filtered,
                "collected": batch.row_count,
                "provider_total": batch.row_count,
                "last_page_fetched": 1,
                "last_page": max(1, (total_filtered + per_page - 1) // per_page),
                "completed": batch.complete,
                "refresh_in_progress": False,
                "status": "HEALTHY" if batch.complete else "DEGRADED",
                "stale": age_seconds > settings.quality.critical_market_stale_seconds,
                "age_seconds": age_seconds,
                "last_success_at": to_utc_iso(source_at),
                "source_key": batch.source_key,
                "trust_tier": batch.trust_tier,
                "batch_trade_eligible": bool(batch.trade_eligible),
                "display_state": display_state,
                "display_only": not currently_trade_eligible,
                "market_session_status": session["status_code"],
                "market_session_status_fa": session["status_fa"],
                "next_open_at_tehran": session["next_open_at_tehran"],
            },
        }

    return {
        "provider": "TSETMC Public CDN",
        "mode": "OFFICIAL",
        "trade_eligible": False,
        "rows": [],
        "meta": {"page": page, "per_page": per_page, "filtered": 0, "collected": 0,
                 "provider_total": 0, "completed": False, "status": "UNAVAILABLE",
                 "stale": True, "source_key": "tsetmc_cdn_market_watch",
                 "display_state": "NO_DATA", "display_only": True,
                 "market_session_status": session["status_code"],
                 "market_session_status_fa": session["status_fa"],
                 "next_open_at_tehran": session["next_open_at_tehran"]},
    }

    receipt = db.query(DataSourceReceipt).filter(
        DataSourceReceipt.source_key == "tindex_symbol_screener_reference"
    ).first()
    metadata = (receipt.metadata_json or {}) if receipt else {}
    stored_rows = metadata.get("symbols") if isinstance(metadata.get("symbols"), list) else []
    allowed_fields = (
        "slug", "ticker", "name_fa", "last_price_rials", "closing_price_rials",
        "change_pct", "volume", "value_rials", "market_cap_rials", "pe", "source_updated_at",
    )
    rows = [
        {field: row.get(field) for field in allowed_fields}
        for row in stored_rows
        if isinstance(row, dict)
    ]
    needle = (q or "").strip()
    if needle:
        rows = [
            row for row in rows
            if needle in str(row.get("ticker") or "") or needle in str(row.get("name_fa") or "")
        ]
    total_filtered = len(rows)
    start = (page - 1) * per_page
    page_rows = rows[start:start + per_page]
    published_at_raw = metadata.get("published_at")
    try:
        published_at = datetime.fromisoformat(str(published_at_raw).replace("Z", "+00:00")) if published_at_raw else None
    except (TypeError, ValueError):
        published_at = None
    last_success = published_at or (receipt.last_success_at if receipt else None)
    if last_success and last_success.tzinfo is None:
        last_success = last_success.replace(tzinfo=timezone.utc)
    age_seconds = max(0, int((now_utc() - last_success.astimezone(timezone.utc)).total_seconds())) if last_success else None
    return {
        "provider": "Tindex",
        "mode": "REFERENCE_ONLY",
        "trade_eligible": False,
        "rows": page_rows,
        "meta": {
            "page": page,
            "per_page": per_page,
            "filtered": total_filtered,
            "collected": int(receipt.record_count if receipt else 0),
            "provider_total": int(metadata.get("total") or 0),
            "last_page_fetched": int(metadata.get("last_page_fetched") or 0),
            "last_page": int(metadata.get("last_page") or 0),
            "completed": bool(metadata.get("completed")),
            "refresh_in_progress": bool(metadata.get("refresh_in_progress")),
            "status": receipt.status if receipt else "UNAVAILABLE",
            "stale": bool(not receipt or receipt.status != "HEALTHY" or age_seconds is None or age_seconds > settings.tindex.screener_refresh_seconds),
            "age_seconds": age_seconds,
            "last_success_at": to_utc_iso(last_success),
        },
    }


@router.get("/overview", response_model=MarketOverviewResponse)
def get_market_overview(db: Session = Depends(get_sync_db)):
    """Returns real-time Tehran stock market session overview, breadth, and regime."""
    # Count opportunities by grade
    a_plus = db.query(PublishedSignal).filter(PublishedSignal.grade == "A+", PublishedSignal.actionable == True).count()
    a_count = db.query(PublishedSignal).filter(PublishedSignal.grade == "A", PublishedSignal.actionable == True).count()
    b_count = db.query(PublishedSignal).filter(PublishedSignal.grade == "B", PublishedSignal.actionable == True).count()

    market_receipt = db.query(DataSourceReceipt).filter(DataSourceReceipt.source_key == "tsetmc_market_watch").first()
    fixture_count = db.query(Instrument).filter(Instrument.is_active == True, Instrument.source_instrument_code.like("INS\\_%", escape="\\")).count()
    latest_snapshot = trusted_market_snapshot_base_query(db).order_by(
        MarketSnapshot.source_timestamp.desc()
    ).first()
    latest_market_at = latest_snapshot.source_timestamp if latest_snapshot else None
    if latest_market_at and latest_market_at.tzinfo is None:
        latest_market_at = latest_market_at.replace(tzinfo=timezone.utc)
    market_age_seconds = max(0, int((now_utc() - latest_market_at.astimezone(timezone.utc)).total_seconds())) if latest_market_at else None
    current_batch = db.get(MarketDataBatch, latest_snapshot.batch_id) if latest_snapshot else None
    official_market_data = bool(market_receipt and market_receipt.status == "HEALTHY" and market_receipt.mode == "official" and fixture_count == 0 and latest_market_at and current_batch)
    fresh_market_data = bool(official_market_data and market_age_seconds is not None and market_age_seconds <= 60)
    reference_meta: dict = {}
    reference_available = False
    health_reasons: list[str] = []
    if fixture_count:
        health_reasons.append("نماد fixture فعال در دیتابیس وجود دارد.")
    if not market_receipt or market_receipt.status != "HEALTHY" or market_receipt.mode != "official":
        health_reasons.append("receipt رسمی سالم market-watch موجود نیست.")
    if latest_market_at is None:
        health_reasons.append("هیچ timestamp منبع بازار ثبت نشده است.")
    elif not fresh_market_data:
        health_reasons.append(f"آخرین داده بازار {market_age_seconds} ثانیه قدمت دارد.")
    if reference_available and not official_market_data:
        health_reasons.append(
            f"نمای جایگزین Tindex مربوط به {reference_meta.get('as_of') or 'زمان نامشخص'} فقط برای نمایش فعال است؛ معامله مسدود می‌ماند."
        )

    # Calculate breadth only from a trusted canonical universe.
    instruments = db.query(Instrument).filter(Instrument.is_active == True).all()
    advancers = 0
    decliners = 0
    unchanged = 0
    total_val = 0.0
    total_vol = 0
    total_pct_sum = 0.0

    current_snapshots = {
        row.instrument_id: row
        for row in trusted_market_snapshot_base_query(db).filter(
            MarketSnapshot.batch_id == current_batch.id
        ).all()
    } if official_market_data and current_batch else {}
    for inst in instruments if official_market_data else []:
        b = current_snapshots.get(inst.id)
        if b:
            total_val += (b.value or 0)
            total_vol += (b.volume or 0)
            yp = b.yesterday_price
            if yp > 0:
                ret = (b.close_price - yp) / yp
                total_pct_sum += ret
                if b.close_price > yp:
                    advancers += 1
                elif b.close_price < yp:
                    decliners += 1
                else:
                    unchanged += 1

    total_inst = advancers + decliners + unchanged
    if reference_available and not official_market_data:
        reference_breadth = reference_meta.get("breadth") or {}
        reference_totals = reference_meta.get("totals") or {}
        advancers = max(0, int(reference_breadth.get("advancing") or 0))
        decliners = max(0, int(reference_breadth.get("declining") or 0))
        unchanged = max(0, int(reference_breadth.get("flat") or 0))
        total_val = max(0.0, float(reference_totals.get("trade_value") or 0))
        total_vol = max(0, int(reference_totals.get("trade_volume") or 0))
        total_inst = advancers + decliners + unchanged
    avg_market_ret = (total_pct_sum / total_inst) * 100.0 if total_inst else 0.0
    index_receipt = db.query(DataSourceReceipt).filter(DataSourceReceipt.source_key == "tsetmc_indices").first()
    indices: list[MarketIndexSummary] = []
    if index_receipt and index_receipt.status == "HEALTHY" and index_receipt.mode == "official" and fixture_count == 0:
        seen_codes: set[str] = set()
        recent_indices = db.query(MarketIndexSnapshot).order_by(MarketIndexSnapshot.source_timestamp.desc()).limit(200).all()
        for item in recent_indices:
            if item.source_index_code in seen_codes:
                continue
            seen_codes.add(item.source_index_code)
            indices.append(MarketIndexSummary(
                name_fa=item.name_fa,
                value=item.value,
                change_pct=item.change_pct,
                change_value=item.change_value,
            ))
    else:
        health_reasons.append("این endpoint عمومی CDN شاخص‌های رسمی را برنمی‌گرداند؛ بخش شاخص بدون داده نمایش داده می‌شود.")

    is_bullish = total_inst > 0 and advancers >= decliners
    regime = ("risk_on" if is_bullish else "risk_off") if official_market_data else "unknown"
    regime_fa = (
        ("رونق و تقاضای پرقدرت (ریسک‌پذیر)" if is_bullish else "اصلاح و احتیاط عمومی (ریسک‌گریز)")
        if official_market_data
        else ("نمای جایگزین Tindex؛ فقط نمایش و بدون مجوز معامله" if reference_available else "نامشخص؛ داده رسمی معتبر در دسترس نیست")
    )
    session = get_market_session_state()

    return MarketOverviewResponse(
        session_status=session["status_code"],
        session_status_fa=session["status_fa"],
        current_time_utc=to_utc_iso(now_utc()),
        current_time_jalali=to_jalali_str(now_utc(), include_time=True),
        indices=indices,
        breadth_advancers=advancers,
        breadth_decliners=decliners,
        breadth_unchanged=unchanged,
        total_volume=total_vol,
        total_value_rials=total_val,
        market_regime=regime,
        market_regime_fa=regime_fa,
        regime_confidence=0.0 if not official_market_data else round(min(100.0, abs(avg_market_ret) * 20 + 50), 1),
        opportunity_count_a_plus=a_plus,
        opportunity_count_a=a_count,
        opportunity_count_b=b_count,
        data_health_status="HEALTHY" if fresh_market_data else ("STALE" if official_market_data else ("REFERENCE_ONLY" if reference_available else "BLOCKED")),
        market_data_as_of_utc=to_utc_iso(latest_market_at),
        market_data_age_seconds=market_age_seconds,
        data_health_reasons_fa=health_reasons,
    )


@router.get("/sectors", response_model=list[SectorScorecard])
def get_sector_scorecard(db: Session = Depends(get_sync_db)):
    """Returns sector performance, cash flow rankings, and momentum."""
    receipt = db.query(DataSourceReceipt).filter(DataSourceReceipt.source_key == "tsetmc_market_watch").first()
    fixture_count = db.query(Instrument).filter(Instrument.is_active == True, Instrument.source_instrument_code.like("INS\\_%", escape="\\")).count()
    if not receipt or receipt.status != "HEALTHY" or receipt.mode != "official" or fixture_count:
        return []
    sectors = db.query(Sector).all()
    measured: list[tuple[Sector, float, float, float, float, int]] = []
    for sec in sectors:
        instruments = db.query(Instrument).filter(
            Instrument.sector_id == sec.id, Instrument.is_active == True
        ).all()
        momentums: list[float] = []
        above_ema = 0
        eligible = 0
        flow = 0.0
        turnover = 0.0
        for instrument in instruments:
            bars = db.query(EODBar).filter(EODBar.instrument_id == instrument.id).order_by(
                EODBar.trading_date.desc()
            ).limit(20).all()
            if len(bars) >= 2 and bars[-1].close > 0:
                momentums.append(((bars[0].close / bars[-1].close) - 1.0) * 100.0)
            if len(bars) >= 20:
                eligible += 1
                above_ema += int(bars[0].close > (sum(bar.close for bar in bars) / len(bars)))
            snapshot = db.query(MarketSnapshot).filter(MarketSnapshot.instrument_id == instrument.id).order_by(
                MarketSnapshot.source_timestamp.desc()
            ).first()
            if snapshot:
                turnover += max(0.0, snapshot.value or 0.0)
            client = db.query(ClientTypeSnapshot).filter(
                ClientTypeSnapshot.instrument_id == instrument.id
            ).order_by(ClientTypeSnapshot.trading_date.desc()).first()
            if client:
                flow += (client.real_buy_value or 0.0) - (client.real_sell_value or 0.0)
        if not momentums or eligible == 0:
            continue
        momentum = sum(momentums) / len(momentums)
        breadth = (above_ema / eligible) * 100.0
        opp_count = (
            db.query(PublishedSignal)
            .join(Instrument, PublishedSignal.instrument_id == Instrument.id)
            .filter(Instrument.sector_id == sec.id)
            .count()
        )
        measured.append((sec, momentum, breadth, flow, turnover, opp_count))

    measured.sort(key=lambda row: (row[1], row[2], row[3]), reverse=True)
    scorecards = []
    for rank, (sec, momentum, breadth, flow, turnover, opp_count) in enumerate(measured, start=1):
        scorecards.append(
            SectorScorecard(
                sector_id=sec.id,
                code=sec.code,
                name_fa=sec.name_fa,
                momentum_20d_pct=round(momentum, 2),
                breadth_pct=round(breadth, 2),
                net_real_inflow_rials=flow,
                turnover_value_rials=turnover,
                opportunity_count=opp_count,
                relative_strength_rank=rank,
            )
        )
    return scorecards


@router.post("/sync-all")
async def sync_all_system(db: Session = Depends(get_sync_db)):
    """
    چرخه سریع داده زنده: جهان نمادها، دیده‌بان لحظه‌ای و شاخص‌ها.
    backfill تاریخی عمداً از این مسیر تعاملی جدا است.
    """
    from services.collector.market_cycle import MarketCycleOrchestrator

    orchestrator = MarketCycleOrchestrator(db)
    try:
        cycle = await orchestrator.run(trigger="manual", allow_paper_trade=True, timeout_seconds=30)
        sync_stats = cycle["sync"]
    except asyncio.TimeoutError as exc:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=504,
            detail="منبع رسمی در مهلت ۳۰ ثانیه پاسخ نداد؛ چرخه بدون ثبت قیمت یا معامله متوقف شد.",
        ) from exc
    except RuntimeError as exc:
        from fastapi import HTTPException
        import re
        error_text = str(exc)
        remaining_match = re.search(r"(\d+) seconds", error_text)
        if remaining_match:
            remaining_minutes = max(1, (int(remaining_match.group(1)) + 59) // 60)
            detail = (
                f"مدار محافظ TSETMC فعال است؛ برای جلوگیری از تمدید مسدودی، تا حدود {remaining_minutes} دقیقه "
                "هیچ درخواست جدیدی فرستاده نمی‌شود. داده و معامله بدون قیمت رسمی متوقف می‌ماند."
            )
        elif "circuit is open" in error_text:
            detail = (
                "دسترسی شبکه به CDN رسمی TSETMC مسدود یا قطع است؛ مدار محافظ برای دو ساعت باز شد و "
                "همه retryهای خودکار متوقف شدند. هیچ قیمت یا معامله‌ای ساخته نشد."
            )
        else:
            detail = (
                "تنها منبع فعال، JSON API رسمی TSETMC است و این منبع از مسیر شبکه فعلی پاسخ معتبر نداد؛ "
                "هیچ fallback یا قیمت ساختگی اجرا نشد و چرخه بدون ثبت قیمت یا معامله متوقف شد."
            )
        raise HTTPException(
            status_code=503,
            detail=detail,
        ) from exc

    opp_count = int(cycle.get("actionable_signal_count") or 0)
    trade_result = cycle.get("trade") or {}

    return {
        "success": True,
        "message": sync_stats.get("message_fa") or "داده‌های رسمی همگام و رادار دوباره محاسبه شد؛ این عملیات به‌تنهایی معامله اجرا نمی‌کند.",
        "opportunity_count": opp_count,
        "sync_stats": sync_stats,
        "trade_cycle_started": bool(trade_result.get("executed")),
        "trade_cycle_evaluated": bool(sync_stats.get("trade_eligible")),
        "trade_result": trade_result,
        "timestamp_jalali": to_jalali_str(now_utc(), include_time=True),
        "timestamp_utc": to_utc_iso(now_utc()),
    }


@router.get("/session-state")
def get_session_state_route():
    """Returns current TSE trading session state, market open status, and adaptive update cadence."""
    from packages.market_rules.trading_hours import get_market_session_state
    return get_market_session_state()
