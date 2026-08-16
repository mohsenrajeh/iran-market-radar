import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.paper_broker.auto_trader import AutoPaperTrader
from services.collector.service import IngestionCoordinator
from packages.shared.database import SyncSessionLocal
from packages.shared.logger import logger

async def main():
    logger.info("Running scan & auto-trader cycle...")
    db = SyncSessionLocal()
    coord = IngestionCoordinator(db)
    coord.run_radar_scan()
    db.close()

    trader = AutoPaperTrader()
    await trader.run_cycle()
    logger.info("Cycle finished successfully!")

if __name__ == "__main__":
    asyncio.run(main())
