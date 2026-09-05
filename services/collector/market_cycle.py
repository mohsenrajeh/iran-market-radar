"""Single bounded market-cycle orchestration entry point."""
from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from packages.domain.models import PublishedSignal
from packages.shared.config import settings
from packages.shared.database import SyncSessionLocal
from packages.shared.datetime_utils import now_utc, to_utc_iso
from services.collector.service import IngestionCoordinator
from services.collector.live_hub import market_live_hub


def _run_radar_scan_isolated() -> tuple[int, int]:
    """Run synchronous feature/scoring work outside the API event loop."""
    db = SyncSessionLocal()
    try:
        produced = IngestionCoordinator(db).run_radar_scan()
        actionable = db.query(PublishedSignal).filter(PublishedSignal.actionable == True).count()
        return len(produced or []), actionable
    finally:
        db.close()


class MarketCycleOrchestrator:
    """Collect once, validate, scan, and optionally run the paper executor."""

    def __init__(self, db: Session):
        self.db = db

    async def run(
        self,
        *,
        trigger: str,
        allow_paper_trade: bool,
        timeout_seconds: int = 45,
    ) -> dict[str, Any]:
        coordinator = IngestionCoordinator(self.db)
        sync_stats = await asyncio.wait_for(coordinator.sync_live_cycle(), timeout=timeout_seconds)
        market_live_hub.publish({
            "type": "market_cycle",
            "provider": "TSETMC_PUBLIC_CDN",
            "market_rows": sync_stats.get("market_rows", 0),
            "batch_id": sync_stats.get("batch_id"),
            "trade_eligible": bool(sync_stats.get("trade_eligible")),
            "published_at_utc": to_utc_iso(now_utc()),
        })
        research_signals = 0
        actionable_signals = 0
        analysis_error: str | None = None
        trade_result: dict[str, Any] = {"executed": False, "reason": "paper_execution_not_requested"}
        codal: dict[str, Any] | None = None

        if sync_stats.get("trade_eligible"):
            codal = await coordinator.sync_codal_disclosures()
            try:
                research_signals, actionable_signals = await asyncio.to_thread(
                    _run_radar_scan_isolated
                )
            except Exception as exc:
                self.db.rollback()
                analysis_error = type(exc).__name__
            if allow_paper_trade and settings.trading_mode == "paper" and not settings.live_trading_enabled:
                from services.paper_broker.auto_trader import auto_trader
                trade_result = await auto_trader.run_cycle(
                    manual=(trigger == "manual"),
                    sync_market=False,
                    provided_sync_stats=sync_stats,
                )
        else:
            # Reference feeds are useful for a live read model, but never get
            # silently promoted to strategy inputs or execution prices.
            research_signals = 0

        return {
            "trigger": trigger,
            "sync": sync_stats,
            "research_signal_count": research_signals,
            "actionable_signal_count": actionable_signals,
            "trade": trade_result,
            "analysis_error": analysis_error,
            "crosscheck": None,
            "codal": codal,
            "finished_at_utc": to_utc_iso(now_utc()),
        }
