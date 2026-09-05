"""Dedicated lifecycle for the market scheduler and history backfill worker."""
from __future__ import annotations

import asyncio
import signal

from packages.shared.config import settings
from packages.shared.logger import logger
from services.collector.backfill_worker import (
    is_history_backfill_running,
    start_history_backfill_worker,
    stop_history_backfill_worker,
)
from services.paper_broker.scheduler import (
    is_scheduler_running,
    start_auto_trading_scheduler,
    stop_auto_trading_scheduler,
)


async def _wait_for_shutdown() -> None:
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for watched_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(watched_signal, stopped.set)
    await stopped.wait()


async def run_workers() -> None:
    """Start the single background-worker owner and stop it gracefully."""
    settings.validate_runtime_security()
    try:
        await start_auto_trading_scheduler()
        await start_history_backfill_worker()
        logger.info(
            "Dedicated worker ready: market_scheduler=%s history_backfill=%s paper_execution=%s",
            is_scheduler_running(),
            is_history_backfill_running(),
            bool(settings.auto_paper_trading_enabled),
        )
        await _wait_for_shutdown()
    finally:
        await stop_auto_trading_scheduler()
        await stop_history_backfill_worker()
        logger.info("Dedicated market workers stopped.")


if __name__ == "__main__":
    asyncio.run(run_workers())
