"""Ordinary-session-only TSETMC collection and paper-trading worker."""
import asyncio
from packages.market_rules.trading_hours import (
    get_market_session_state,
    is_tse_market_open,
)
from packages.shared.logger import logger

_is_running = False
_bg_task: asyncio.Task | None = None
_apscheduler_instance = None


async def _asyncio_dynamic_worker():
    """
    Run one bulk live cycle per minute only in the ordinary market session.

    Outside 09:00-12:30 Tehran the worker sleeps until the next open and does
    not even construct a collector, so startup/night/weekend cannot touch the
    TSETMC upstream.
    """
    global _is_running
    from packages.shared.config import settings
    from packages.shared.database import SyncSessionLocal
    from services.collector.market_cycle import MarketCycleOrchestrator

    logger.info("🚀 Dynamic adaptive auto-trading background worker started.")

    while _is_running:
        state = get_market_session_state()
        if not state["upstream_requests_allowed"]:
            logger.info(
                "TSETMC collection sleeping: state=%s next_open=%s seconds=%s",
                state["status_code"],
                state["next_open_at_tehran"],
                state["seconds_until_next_open"],
            )
            await _sleep_responsive(state["seconds_until_next_open"])
            continue
        sleep_seconds = 60
        try:
            logger.info(
                "Market open; starting one bounded TSETMC cycle (cadence=%ss).",
                state["cadence_seconds"],
            )
            db = SyncSessionLocal()
            try:
                cycle = await MarketCycleOrchestrator(db).run(
                    trigger="scheduler",
                    allow_paper_trade=bool(settings.auto_paper_trading_enabled and is_tse_market_open()),
                )
                logger.info(
                    "Market data cycle completed: provider=%s rows=%s trade_eligible=%s",
                    ",".join(cycle["sync"].get("providers") or []),
                    cycle["sync"].get("market_rows") or cycle["sync"].get("reference_symbols_collected") or 0,
                    bool(cycle["sync"].get("trade_eligible")),
                )
            finally:
                db.close()
        except Exception as e:
            retry_after = getattr(e, "retry_after_seconds", None)
            if retry_after is not None:
                sleep_seconds = max(1, int(retry_after))
                logger.warning(
                    "TSETMC cycle paused by circuit breaker: %s retry_after=%ss",
                    str(e),
                    sleep_seconds,
                )
            else:
                logger.error(
                    "Market background cycle failed closed: %s: %s",
                    type(e).__name__,
                    str(e),
                )

        await _sleep_responsive(sleep_seconds)


async def _sleep_responsive(seconds: int) -> None:
    """Sleep without upstream work while remaining promptly cancellable."""
    remaining = max(1, int(seconds))
    while _is_running and remaining > 0:
        step = min(30, remaining)
        await asyncio.sleep(step)
        remaining -= step


async def start_auto_trading_scheduler():
    """Starts the always-on data worker; paper execution remains separately gated."""
    global _is_running, _bg_task, _apscheduler_instance

    from packages.shared.config import settings
    if not settings.market_data_scheduler_enabled:
        logger.warning("Market-data scheduler is disabled by configuration.")
        return
    if _is_running:
        logger.info("Auto-trading scheduler is already running.")
        return

    _is_running = True
    _bg_task = asyncio.create_task(_asyncio_dynamic_worker())
    logger.info("🚀 Adaptive market-aware auto-trading scheduler activated.")


async def stop_auto_trading_scheduler():
    """Gracefully shuts down the scheduler or background worker."""
    global _is_running, _bg_task, _apscheduler_instance
    _is_running = False

    if _apscheduler_instance is not None and _apscheduler_instance.running:
        _apscheduler_instance.shutdown(wait=False)
        _apscheduler_instance = None
        logger.info("⏹️ APScheduler auto-trading stopped.")

    if _bg_task is not None:
        _bg_task.cancel()
        _bg_task = None
        logger.info("⏹️ Asyncio background task stopped.")


def is_scheduler_running() -> bool:
    """Returns True if the scheduler or background worker is active."""
    return _is_running
