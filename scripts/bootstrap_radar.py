"""End-to-End Bootstrapper and Verification Script for Iran Market Radar."""
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from packages.domain.models import Instrument, Sector, PublishedSignal, Portfolio
from services.collector.service import IngestionCoordinator
from packages.shared.database import init_db_sync, SyncSessionLocal
from packages.shared.logger import logger


async def main():
    logger.info("==================================================")
    logger.info("🚀 Starting Iran Market Radar System Bootstrap...")
    logger.info("==================================================")

    # 1. Initialize DB Schema
    logger.info("Step 1: Initializing Database Schema...")
    init_db_sync()

    db = SyncSessionLocal()
    try:
        coordinator = IngestionCoordinator(db)

        # 2. Sync Reference Data & Historical Bars
        logger.info("Step 2: Syncing 260 sessions of historical TSE data & حقیقی/حقوقی flows...")
        await coordinator.sync_all_data(history_days=260)

        # 3. Compute Features & Run Opportunity Radar Scan
        logger.info("Step 3: Calculating deterministic features and running strategy catalog...")
        signals = coordinator.run_radar_scan()

        logger.info(f"✅ Scanning complete! Generated {len(signals)} published opportunities.")

        # 4. Inspect Top Signals
        logger.info("--------------------------------------------------")
        logger.info("🏆 Top 5 Opportunities in Iranian Market:")
        for idx, sig in enumerate(signals[:5], 1):
            logger.info(
                f"  {idx}. {sig.symbol} ({sig.name_fa}) | Grade: {sig.grade} | "
                f"Score: {sig.opportunity_score}/100 | p_profit: {int(sig.p_profit * 100)}% | "
                f"Entry: {sig.entry_zone.get('low'):,} - {sig.entry_zone.get('high'):,} Rials"
            )
        logger.info("--------------------------------------------------")

        # 5. Check Paper Trading Portfolio
        port = db.query(Portfolio).first()
        if port:
            logger.info(f"💼 Paper Portfolio Active | Cash: {port.cash:,.0f} Rials | Mode: {port.mode}")

        logger.info("==================================================")
        logger.info("🎉 Iran Market Radar is fully operational!")
        logger.info("==================================================")

    except Exception as ex:
        logger.error(f"Fatal error during bootstrap: {ex}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
