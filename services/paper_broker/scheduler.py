"""Hourly CronJob and dynamic background worker for automated paper trading.
Supports market-aware intervals: more frequent during trading hours (09:00 - 12:30),
less frequent during night and weekend sessions.
"""
import asyncio
from datetime import datetime
from packages.market_rules.trading_hours import (
    get_market_session_state,
    get_dynamic_scheduler_cadence_seconds,
    is_tse_market_open,
)
from packages.shared.logger import logger

_is_running = False
_bg_task: asyncio.Task | None = None
_apscheduler_instance = None


async def _asyncio_dynamic_worker():
    """
    Dynamic background worker that automatically adjusts scan frequency:
    - During TSE trading hours (09:00 - 12:30, Sat-Wed): Runs every 15 minutes
    - During pre-market (08:45 - 09:00): Runs every 30 minutes
    - Outside trading hours (afternoons/nights): Runs every 60 minutes
    - On weekends (Thu-Fri): Runs every 120 minutes
    """
    global _is_running
    from services.paper_broker.auto_trader import auto_trader

    logger.info("🚀 Dynamic adaptive auto-trading background worker started.")

    while _is_running:
        try:
            state = get_market_session_state()
            logger.info(
                f"⏰ Market State: {state['status_fa']} | Cadence: every {state['auto_trade_interval_minutes']} min"
            )
            await auto_trader.run_cycle()
        except Exception as e:
            logger.error(f"Error in auto-trading background cycle: {e}")

        # Determine wait duration dynamically
        sleep_seconds = get_dynamic_scheduler_cadence_seconds()
        
        # Sleep in 5-second responsive slices so shutdown/cancel is immediate
        steps = max(1, sleep_seconds // 5)
        for _ in range(steps):
            if not _is_running:
                break
            await asyncio.sleep(5)


async def start_auto_trading_scheduler():
    """Starts the dynamic auto-trading worker inside the FastAPI process."""
    global _is_running, _bg_task, _apscheduler_instance

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
