"""Trigger a single trading scan and auto-trading execution cycle."""
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from services.paper_broker.auto_trader import auto_trader

async def main():
    print("Executing one radar and auto-trader cycle...")
    await auto_trader.run_cycle()
    print("Cycle execution completed.")

if __name__ == "__main__":
    asyncio.run(main())
