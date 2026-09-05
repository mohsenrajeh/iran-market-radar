"""Resumable official CDN history backfill with cross-source identity verification."""
from __future__ import annotations

import asyncio
import math
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func

from packages.data_adapters.tsetmc_cdn_history import TsetmcCdnHistoryAdapter
from packages.domain.models import (
    ClientTypeSnapshot, DataSourceReceipt, EODBar, Instrument, MarketDataBatch,
    MarketSnapshot,
)
from packages.shared.config import settings
from packages.shared.database import SyncSessionLocal
from packages.shared.datetime_utils import now_utc
from packages.shared.logger import logger
from packages.market_rules.trading_hours import get_market_session_state
from services.collector.trusted_queries import trusted_eod_base_query

_running = False
_task: asyncio.Task | None = None
_last_scan_at: datetime | None = None


def _official_available_at(day: date) -> datetime:
    return datetime.combine(day, time(13, 0), tzinfo=ZoneInfo("Asia/Tehran")).astimezone(timezone.utc)


def _identity_matches(instrument: Instrument, ins_code: str, identity: dict | None) -> bool:
    return bool(
        identity
        and identity.get("ins_code") == ins_code
        and identity.get("isin") == instrument.isin
        and identity.get("ticker_normalized") == instrument.ticker_normalized
    )


async def _fetch_pair(ins_code: str):
    adapter = TsetmcCdnHistoryAdapter(timeout_seconds=max(10, settings.tsetmc.request_timeout_seconds))
    identity = await adapter.fetch_instrument_identity(ins_code)
    if identity is None:
        return [], [], None, adapter.last_error
    # One symbol is one paced job.  Keeping the two large history downloads
    # sequential ensures max_symbols is also the real HTTP concurrency limit.
    eod = await adapter.fetch_eod_history(
        ins_code, days=settings.strategy_engine.min_history_sessions
    )
    eod_error = adapter.last_error
    client = await adapter.fetch_client_type_history(
        ins_code, days=settings.strategy_engine.min_history_sessions
    )
    return eod, client, identity, {
        "eod": eod_error,
        "client": adapter.last_error,
    }


def _short_history_terminal_details(
    bars: list,
    error: dict | str | None,
    required: int,
) -> dict | None:
    """Classify only a non-empty, contract-valid short history, never an outage."""
    eod_error = error.get("eod") if isinstance(error, dict) else error
    if not bars or eod_error or len(bars) >= required:
        return None
    missing_sessions = required - len(bars)
    retry_days = max(7, math.ceil(missing_sessions * 7 / 5))
    return {
        "reason": "insufficient_listing_history",
        "eod_rows": len(bars),
        "required_rows": required,
        "eligible_after": (now_utc() + timedelta(days=retry_days)).isoformat(),
    }


def _run_radar_scan_isolated() -> int:
    """Run CPU/sync-DB analysis outside Uvicorn's event loop and session."""
    from services.collector.service import IngestionCoordinator

    scan_db = SyncSessionLocal()
    try:
        return len(IngestionCoordinator(scan_db).run_radar_scan())
    finally:
        scan_db.close()


def _persist_history_progress(
    db,
    receipt: DataSourceReceipt | None,
    *,
    required: int,
    completed: int,
    rejected: int,
    rejected_until: dict,
    terminal_ineligible: dict,
) -> tuple[DataSourceReceipt, int, int]:
    """Persist truthful progress even when no remote target is currently runnable."""
    active_ids = {
        row[0] for row in db.query(Instrument.id).filter(Instrument.is_active == True).all()
    }
    total_ready = (
        trusted_eod_base_query(db)
        .with_entities(EODBar.instrument_id)
        .group_by(EODBar.instrument_id)
        .having(func.count(EODBar.id) >= required)
        .count()
    )
    terminal_ineligible = {
        instrument_id: details
        for instrument_id, details in terminal_ineligible.items()
        if instrument_id in active_ids
    }
    eligible_expected = max(0, len(active_ids) - len(terminal_ineligible))
    completeness = total_ready / max(1, eligible_expected)
    if receipt is None:
        receipt = DataSourceReceipt(
            source_key="tsetmc_eod", source_kind="market", provider_name="TSETMC Public CDN",
            mode="official", status="DEGRADED", schema_version="tsetmc-cdn-history-v1",
        )
        db.add(receipt)
    receipt.status = (
        "HEALTHY"
        if eligible_expected and completeness >= settings.quality.minimum_symbol_completeness_ratio
        else "DEGRADED"
    )
    receipt.record_count = trusted_eod_base_query(db).count()
    receipt.last_attempt_at = now_utc()
    receipt.last_success_at = now_utc() if completed else receipt.last_success_at
    receipt.error_message = None if completed else "No additional eligible history batch passed the bridge check."
    receipt.metadata_json = {
        "symbols_ready": total_ready,
        "expected_symbols": len(active_ids),
        "eligible_expected_symbols": eligible_expected,
        "terminal_ineligible_count": len(terminal_ineligible),
        "terminal_ineligible": terminal_ineligible,
        "completeness_ratio": completeness,
        "last_batch_completed": completed,
        "last_batch_rejected": rejected,
        "bridge_check": "history_identity_and_latest_close_match_live_cdn",
        "recent_rejections": rejected_until,
        "rejection_cooldown_hours": 1,
    }
    db.commit()
    return receipt, total_ready, eligible_expected


async def run_backfill_batch(*, max_symbols: int = 4) -> dict:
    """Backfill the highest-turnover missing symbols; safe to call repeatedly."""
    session = get_market_session_state()
    if settings.tsetmc_market_hours_enforced and not session["upstream_requests_allowed"]:
        return {
            "processed": 0,
            "reason": "market_closed",
            "retry_after_seconds": session["seconds_until_next_open"],
            "next_open_at_tehran": session["next_open_at_tehran"],
        }
    db = SyncSessionLocal()
    try:
        market_receipt = db.query(DataSourceReceipt).filter(
            DataSourceReceipt.source_key == "tsetmc_market_watch"
        ).first()
        circuit_until_raw = (
            (market_receipt.metadata_json or {}).get("circuit_open_until")
            if market_receipt else None
        )
        if circuit_until_raw:
            try:
                circuit_until = datetime.fromisoformat(str(circuit_until_raw))
                if circuit_until.tzinfo is None:
                    circuit_until = circuit_until.replace(tzinfo=timezone.utc)
                remaining = int((circuit_until - now_utc()).total_seconds())
                if remaining > 0:
                    return {
                        "processed": 0,
                        "reason": "tsetmc_circuit_open",
                        "retry_after_seconds": remaining,
                    }
            except ValueError:
                pass
        receipt = db.query(DataSourceReceipt).filter(
            DataSourceReceipt.source_key == "tsetmc_eod"
        ).first()
        previous_metadata = dict(receipt.metadata_json or {}) if receipt else {}
        raw_terminal_ineligible = dict(previous_metadata.get("terminal_ineligible") or {})
        terminal_ineligible = {}
        for instrument_id, details in raw_terminal_ineligible.items():
            if not isinstance(details, dict) or int(details.get("eod_rows") or 0) <= 0:
                continue
            try:
                eligible_after = datetime.fromisoformat(str(details.get("eligible_after") or ""))
                if eligible_after.tzinfo is None:
                    eligible_after = eligible_after.replace(tzinfo=timezone.utc)
                if eligible_after <= now_utc():
                    continue
            except (TypeError, ValueError):
                continue
            terminal_ineligible[str(instrument_id)] = details
        # Retry transient bridge failures hourly. Symbols that are proven to
        # have short listing history are classified as terminal below instead.
        rejection_cooldown = timedelta(hours=1)
        cutoff = now_utc() - rejection_cooldown
        rejected_until = {}
        for instrument_id, rejected_at_raw in dict(
            previous_metadata.get("recent_rejections") or {}
        ).items():
            try:
                rejected_at = datetime.fromisoformat(str(rejected_at_raw))
                if rejected_at.tzinfo is None:
                    rejected_at = rejected_at.replace(tzinfo=timezone.utc)
                if rejected_at >= cutoff:
                    rejected_until[str(instrument_id)] = rejected_at.astimezone(timezone.utc).isoformat()
            except (TypeError, ValueError):
                continue

        required = settings.strategy_engine.min_history_sessions
        ready_counts = dict(
            trusted_eod_base_query(db)
            .with_entities(EODBar.instrument_id, func.count(EODBar.id))
            .group_by(EODBar.instrument_id)
            .all()
        )
        latest_per_instrument = (
            db.query(
                MarketSnapshot.instrument_id.label("instrument_id"),
                func.max(MarketSnapshot.source_timestamp).label("latest_at"),
            )
            .join(MarketDataBatch, MarketDataBatch.id == MarketSnapshot.batch_id)
            .filter(
                MarketSnapshot.trade_eligible == True,
                MarketSnapshot.trust_tier == "OFFICIAL_DIRECT",
                MarketSnapshot.batch_id.isnot(None),
                MarketDataBatch.source_key == "tsetmc_cdn_market_watch",
                MarketDataBatch.schema_version == "tsetmc-cdn-market-watch-v1",
                MarketDataBatch.complete == True,
                MarketDataBatch.trade_eligible == True,
                MarketDataBatch.trust_tier == "OFFICIAL_DIRECT",
            )
            .group_by(MarketSnapshot.instrument_id)
            .subquery()
        )
        latest_snapshots = (
            db.query(MarketSnapshot)
            .join(MarketDataBatch, MarketDataBatch.id == MarketSnapshot.batch_id)
            .join(
                latest_per_instrument,
                (MarketSnapshot.instrument_id == latest_per_instrument.c.instrument_id)
                & (MarketSnapshot.source_timestamp == latest_per_instrument.c.latest_at),
            )
            .filter(
                MarketDataBatch.source_key == "tsetmc_cdn_market_watch",
                MarketDataBatch.schema_version == "tsetmc-cdn-market-watch-v1",
                MarketDataBatch.complete == True,
                MarketDataBatch.trade_eligible == True,
                MarketDataBatch.trust_tier == "OFFICIAL_DIRECT",
            )
            .order_by(MarketSnapshot.value.desc())
            .all()
        )
        seen: set[str] = set()
        targets: list[dict] = []
        for snapshot in latest_snapshots:
            if snapshot.instrument_id in seen or ready_counts.get(snapshot.instrument_id, 0) >= required:
                continue
            seen.add(snapshot.instrument_id)
            if snapshot.instrument_id in rejected_until:
                continue
            instrument = db.get(Instrument, snapshot.instrument_id)
            if not instrument or not instrument.is_active:
                continue
            # Numeric InsCode comes directly from the official CDN market row.
            ins_code = str(instrument.source_instrument_code or "")
            if not ins_code.isdigit():
                continue
            targets.append({
                "instrument_id": instrument.id,
                "ins_code": ins_code,
                "yesterday_price": float(snapshot.yesterday_price),
                "snapshot_at": snapshot.source_timestamp,
            })
            if len(targets) >= max_symbols:
                break
        if not targets:
            _, total_ready, eligible_expected = _persist_history_progress(
                db, receipt, required=required, completed=0, rejected=0,
                rejected_until=rejected_until, terminal_ineligible=terminal_ineligible,
            )
            return {
                "processed": 0,
                "reason": "complete_or_identity_unavailable",
                "symbols_ready": total_ready,
                "expected": eligible_expected,
            }

        # Never hold a PostgreSQL transaction/row lock while awaiting remote
        # CDN I/O.  A suspended SyncSession transaction can deadlock API reads
        # and migrations even though the event loop itself is healthy.
        db.commit()
        db.close()
        results = await asyncio.gather(*[_fetch_pair(item["ins_code"]) for item in targets])
        db = SyncSessionLocal()
        receipt = db.query(DataSourceReceipt).filter(
            DataSourceReceipt.source_key == "tsetmc_eod"
        ).first()
        completed = 0
        rejected = 0
        for target, (bars, client_rows, identity, error) in zip(targets, results):
            instrument = db.get(Instrument, target["instrument_id"])
            ins_code = target["ins_code"]
            if instrument is None:
                rejected += 1
                continue
            if not _identity_matches(instrument, ins_code, identity):
                rejected += 1
                rejected_until[instrument.id] = now_utc().isoformat()
                continue
            if len(bars) < required:
                terminal_details = _short_history_terminal_details(bars, error, required)
                if terminal_details is not None:
                    terminal_ineligible[instrument.id] = terminal_details
                else:
                    rejected_until[instrument.id] = now_utc().isoformat()
                rejected += 1
                continue
            if len(client_rows) < int(required * 0.80):
                rejected += 1
                rejected_until[instrument.id] = now_utc().isoformat()
                continue
            latest_bar = bars[0]
            latest_client = client_rows[0]
            tolerance = max(1.0, target["yesterday_price"] * 0.001)
            if (
                latest_bar["trading_date"] != latest_client["trading_date"]
                or abs(float(latest_bar["close"]) - target["yesterday_price"]) > tolerance
                or date.fromisoformat(latest_bar["trading_date"]) >= target["snapshot_at"].date()
            ):
                rejected += 1
                rejected_until[instrument.id] = now_utc().isoformat()
                continue
            batch = MarketDataBatch(
                source_key="tsetmc_cdn_history",
                provider_name="TSETMC Public CDN",
                source_timestamp=target["snapshot_at"],
                received_at=now_utc(), mode="official", trust_tier="OFFICIAL_DIRECT",
                trade_eligible=True, schema_version="tsetmc-cdn-history-v1",
                row_count=len(bars) + len(client_rows), complete=True,
                metadata_json={
                    "instrument_id": instrument.id, "ins_code": ins_code,
                    "bridge_check": "history_identity_and_latest_close_match_live_cdn",
                    "eod_rows": len(bars), "client_rows": len(client_rows),
                },
            )
            db.add(batch)
            db.flush()
            for row in reversed(bars):
                trading_date = date.fromisoformat(row["trading_date"])
                existing = db.query(EODBar).filter(
                    EODBar.instrument_id == instrument.id,
                    EODBar.trading_date == trading_date,
                ).first()
                if existing:
                    continue
                db.add(EODBar(
                    instrument_id=instrument.id, trading_date=trading_date,
                    open=row["open"], high=row["high"], low=row["low"], close=row["close"],
                    last=row["last"], yesterday_price=row["yesterday_price"],
                    volume=row["volume"], value=row["value"], trade_count=row["trade_count"],
                    allowed_min=None, allowed_max=None, available_at=_official_available_at(trading_date),
                    ingested_at=now_utc(), source_key="tsetmc_cdn_history", batch_id=batch.id,
                    trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
                ))
            for row in reversed(client_rows):
                trading_date = date.fromisoformat(row["trading_date"])
                existing = db.query(ClientTypeSnapshot).filter(
                    ClientTypeSnapshot.instrument_id == instrument.id,
                    ClientTypeSnapshot.trading_date == trading_date,
                ).first()
                if existing:
                    continue
                db.add(ClientTypeSnapshot(
                    instrument_id=instrument.id, trading_date=trading_date,
                    real_buy_count=row["real_buy_count"], real_buy_volume=row["real_buy_volume"], real_buy_value=row["real_buy_value"],
                    real_sell_count=row["real_sell_count"], real_sell_volume=row["real_sell_volume"], real_sell_value=row["real_sell_value"],
                    legal_buy_count=row["legal_buy_count"], legal_buy_volume=row["legal_buy_volume"], legal_buy_value=row["legal_buy_value"],
                    legal_sell_count=row["legal_sell_count"], legal_sell_volume=row["legal_sell_volume"], legal_sell_value=row["legal_sell_value"],
                    available_at=_official_available_at(trading_date), source_key="tsetmc_cdn_history",
                    batch_id=batch.id, trust_tier="OFFICIAL_DIRECT", trade_eligible=True,
                ))
            db.commit()
            completed += 1

        receipt, total_ready, eligible_expected = _persist_history_progress(
            db, receipt, required=required, completed=completed, rejected=rejected,
            rejected_until=rejected_until, terminal_ineligible=terminal_ineligible,
        )
        signals = 0
        analysis_error = None
        global _last_scan_at
        scan_due = _last_scan_at is None or (now_utc() - _last_scan_at).total_seconds() >= 60
        if completed and total_ready >= 5 and scan_due:
            try:
                signals = await asyncio.to_thread(_run_radar_scan_isolated)
                _last_scan_at = now_utc()
            except Exception as exc:
                analysis_error = type(exc).__name__
        return {"processed": completed, "rejected": rejected, "symbols_ready": total_ready, "expected": eligible_expected, "signals": signals, "analysis_error": analysis_error}
    finally:
        db.close()


async def _worker():
    global _running
    logger.info("Official CDN resumable history worker started.")
    while _running:
        try:
            # One paced symbol job prevents history enrichment from bursting
            # alongside the minute bulk live request.
            result = await run_backfill_batch(max_symbols=1)
            logger.info("History backfill progress: %s", result)
            if result.get("reason") == "market_closed":
                delay = int(result.get("retry_after_seconds") or 60)
            elif result.get("reason") == "tsetmc_circuit_open":
                delay = int(result.get("retry_after_seconds") or 60)
            else:
                delay = max(60, settings.history_backfill_interval_seconds)
        except Exception as exc:
            logger.error("History backfill batch failed: %s", type(exc).__name__)
            delay = 60
        remaining = max(1, delay)
        while _running and remaining > 0:
            step = min(30, remaining)
            await asyncio.sleep(step)
            remaining -= step


async def start_history_backfill_worker():
    global _running, _task
    if not settings.history_backfill_enabled:
        logger.warning("Official CDN history backfill is disabled by configuration.")
        return
    if _running:
        return
    _running = True
    _task = asyncio.create_task(_worker())


async def stop_history_backfill_worker():
    global _running, _task
    _running = False
    if _task:
        _task.cancel()
        _task = None


def is_history_backfill_running() -> bool:
    """Return whether this process currently owns the history worker."""
    return _running
