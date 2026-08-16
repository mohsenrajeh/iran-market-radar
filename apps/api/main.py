"""FastAPI Main Server Application for Iran Market Radar."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes.overview import router as overview_router
from apps.api.routes.opportunities import router as opportunities_router
from apps.api.routes.symbols import router as symbols_router
from apps.api.routes.strategies import router as strategies_router
from apps.api.routes.backtests import router as backtests_router
from apps.api.routes.paper import router as paper_router
from apps.api.routes.health import router as health_router
from apps.api.routes.settings import router as settings_router
from apps.api.routes.auto_trading import router as auto_trading_router
from apps.api.routes.fundamentals import router as fundamentals_router
from apps.api.routes.auth import router as auth_router
from apps.api.routes.history import router as history_router
from apps.api.routes.learning import router as learning_router
from services.collector.service import IngestionCoordinator
from services.paper_broker.scheduler import start_auto_trading_scheduler, stop_auto_trading_scheduler
from packages.shared.config import settings
from packages.shared.database import init_db_sync, SyncSessionLocal
from packages.shared.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup data bootstrapping."""
    logger.info("Initializing Iran Market Radar database and models...")
    init_db_sync()

    # Bootstrap default seed data if DB is fresh
    db = SyncSessionLocal()
    try:
        coordinator = IngestionCoordinator(db)
        await coordinator.sync_all_data(history_days=260)
        coordinator.run_radar_scan()
        logger.info("Iran Market Radar initialized and ready.")
    except Exception as ex:
        logger.error(f"Error during bootstrapping: {ex}", exc_info=True)
    finally:
        db.close()

    # Start auto-trading scheduler (hourly CronJob)
    try:
        await start_auto_trading_scheduler()
        logger.info("Auto-trading scheduler activated.")
    except Exception as ex:
        logger.error(f"Failed to start auto-trading scheduler: {ex}", exc_info=True)

    yield

    # Shutdown scheduler gracefully
    await stop_auto_trading_scheduler()
    logger.info("Shutting down Iran Market Radar API server.")


app = FastAPI(
    title="Iran Market Radar API",
    description="Institutional-grade Iranian Stock Market scanner, backtester and probability calibrator.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for Next.js web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes under /api/v1
API_PREFIX = "/api/v1"
app.include_router(overview_router, prefix=API_PREFIX)
app.include_router(opportunities_router, prefix=API_PREFIX)
app.include_router(symbols_router, prefix=API_PREFIX)
app.include_router(strategies_router, prefix=API_PREFIX)
app.include_router(backtests_router, prefix=API_PREFIX)
app.include_router(paper_router, prefix=API_PREFIX)
app.include_router(auto_trading_router, prefix=API_PREFIX)
app.include_router(fundamentals_router, prefix=API_PREFIX)
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(settings_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(history_router, prefix=API_PREFIX)
app.include_router(learning_router, prefix=API_PREFIX)



@app.get("/")
def root_redirect():
    return {
        "name": "Iran Market Radar API",
        "status": "online",
        "docs": "/docs",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=settings.app_port, reload=True)
