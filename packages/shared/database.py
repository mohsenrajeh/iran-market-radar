"""SQLAlchemy 2.0 database connection and session management."""
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from packages.shared.config import settings


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""
    pass


# Synchronous and Asynchronous engines with graceful SQLite fallback for local testing
try:
    async_engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
    )
except Exception:
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///./iran_market_radar.db",
        echo=False,
        future=True,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

import os

# Synchronous engine
try:
    sync_url = settings.database_sync_url
    # If running outside docker on host where postgres container is mapped to 5742 or sqlite is preferred
    if "@postgres:" in sync_url and not os.path.exists("/.dockerenv"):
        try:
            # Try connecting to local postgres port 5742 first
            host_pg_url = sync_url.replace("@postgres:5432", "@127.0.0.1:5742")
            test_engine = create_engine(host_pg_url, connect_args={"connect_timeout": 2})
            with test_engine.connect():
                pass
            sync_url = host_pg_url
        except Exception:
            sync_url = "sqlite:///./iran_market_radar.db"

    sync_engine = create_engine(
        sync_url,
        echo=False,
        future=True,
    )
except Exception:
    sync_engine = create_engine(
        "sqlite:///./iran_market_radar.db",
        echo=False,
        future=True,
    )

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db():
    """Generator for sync DB session."""
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


async def init_db():
    """Initializes all database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db_sync():
    """Initializes all database tables synchronously and applies safe column additions."""
    from sqlalchemy import text
    Base.metadata.create_all(bind=sync_engine)

    # Safe column migrations for existing Postgres tables
    migration_statements = [
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS total_invested_rials FLOAT DEFAULT 0.0",
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS risk_pct FLOAT DEFAULT 0.0",
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS risk_reward_ratio VARCHAR(32) DEFAULT '1:2'",
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS expected_days_to_target INTEGER DEFAULT 5",
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS market_regime VARCHAR(32) DEFAULT 'bullish'",
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS decision_method VARCHAR(128) DEFAULT ''",
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS entry_reason_fa TEXT DEFAULT ''",
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS risk_flags_fa JSON DEFAULT '[]'::json",
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS client_power_ratio FLOAT DEFAULT 1.0",
        "ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS initial_cash FLOAT DEFAULT 10000000000.0",
        "ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS kill_switch_active BOOLEAN DEFAULT FALSE",
        "ALTER TABLE filing ADD COLUMN IF NOT EXISTS symbol VARCHAR(64) DEFAULT ''",
        "ALTER TABLE filing ADD COLUMN IF NOT EXISTS filing_type_fa VARCHAR(128) DEFAULT ''",
        "ALTER TABLE filing ADD COLUMN IF NOT EXISTS sentiment VARCHAR(32) DEFAULT 'neutral'",
        "ALTER TABLE filing ADD COLUMN IF NOT EXISTS sentiment_fa VARCHAR(64) DEFAULT 'خنثی'",
        "ALTER TABLE filing ADD COLUMN IF NOT EXISTS impact_score FLOAT DEFAULT 5.0",
        "ALTER TABLE filing ADD COLUMN IF NOT EXISTS summary_fa TEXT DEFAULT ''",
        "ALTER TABLE published_signal ADD COLUMN IF NOT EXISTS current_price FLOAT DEFAULT 0.0",
    ]

    with sync_engine.begin() as conn:
        for stmt in migration_statements:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
