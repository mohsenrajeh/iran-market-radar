import asyncio
from unittest.mock import AsyncMock, Mock


def test_dedicated_worker_owns_startup_and_shutdown(monkeypatch):
    import services.worker_main as worker_main

    validate = Mock()
    start_market = AsyncMock()
    start_history = AsyncMock()
    stop_market = AsyncMock()
    stop_history = AsyncMock()

    monkeypatch.setattr(
        type(worker_main.settings),
        "validate_runtime_security",
        lambda _settings: validate(),
    )
    monkeypatch.setattr(worker_main, "start_auto_trading_scheduler", start_market)
    monkeypatch.setattr(worker_main, "start_history_backfill_worker", start_history)
    monkeypatch.setattr(worker_main, "stop_auto_trading_scheduler", stop_market)
    monkeypatch.setattr(worker_main, "stop_history_backfill_worker", stop_history)
    monkeypatch.setattr(worker_main, "is_scheduler_running", lambda: False)
    monkeypatch.setattr(worker_main, "is_history_backfill_running", lambda: False)
    monkeypatch.setattr(worker_main, "_wait_for_shutdown", AsyncMock())

    asyncio.run(worker_main.run_workers())

    validate.assert_called_once_with()
    start_market.assert_awaited_once_with()
    start_history.assert_awaited_once_with()
    stop_market.assert_awaited_once_with()
    stop_history.assert_awaited_once_with()


def test_coolify_api_startup_does_not_initialize_database(monkeypatch):
    from apps.api import main

    initialize = Mock()
    coordinator = Mock()
    coordinator.bootstrap_if_empty = AsyncMock()
    db = Mock()
    monkeypatch.setattr(main.settings, "database_startup_init_enabled", False)
    monkeypatch.setattr(main, "init_db_sync", initialize)
    monkeypatch.setattr(main, "SyncSessionLocal", lambda: db)
    monkeypatch.setattr(main, "IngestionCoordinator", lambda _db: coordinator)
    for name in (
        "start_auto_trading_scheduler", "start_history_backfill_worker",
        "stop_auto_trading_scheduler", "stop_history_backfill_worker",
    ):
        monkeypatch.setattr(main, name, AsyncMock())

    async def startup_shutdown():
        async with main.lifespan(main.app):
            pass

    asyncio.run(startup_shutdown())
    initialize.assert_not_called()
    coordinator.bootstrap_if_empty.assert_not_awaited()
    db.close.assert_called_once_with()
