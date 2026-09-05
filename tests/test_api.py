"""Integration tests for FastAPI endpoints."""
import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from apps.api.main import app
from packages.shared.database import init_db_sync
from apps.api.routes.auth import create_access_token

init_db_sync()
client = TestClient(app)
client.cookies.set("radar_session", create_access_token({"sub": "test-admin", "role": "admin"}))


def test_api_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_api_market_overview():
    res = client.get("/api/v1/market/overview")
    assert res.status_code == 200
    data = res.json()
    assert "session_status" in data
    assert "indices" in data
    assert isinstance(data["indices"], list)
    assert data["data_health_status"] in {"HEALTHY", "STALE", "BLOCKED", "REFERENCE_ONLY"}


def test_api_opportunities():
    res = client.get("/api/v1/opportunities")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "opportunity_score" in item
        assert "p_profit" in item
        assert "confidence" in item
        assert "signal_strength" in item
        assert "entry_zone" in item
        assert "invalidation" in item


def test_api_strategies():
    res = client.get("/api/v1/strategies")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 8


def test_api_settings():
    res = client.get("/api/v1/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["trading_mode"] == "paper"
    assert data["live_trading_enabled"] is False


def test_private_read_requires_admin_session():
    anonymous = TestClient(app)
    res = anonymous.get("/api/v1/paper/portfolio")
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"


def test_private_read_rejects_malformed_or_non_admin_token():
    malformed = TestClient(app)
    malformed.cookies.set("radar_session", "not-a-jwt")
    assert malformed.get("/api/v1/settings").status_code == 401

    non_admin = TestClient(app)
    non_admin.cookies.set("radar_session", create_access_token({"sub": "viewer", "role": "viewer"}))
    assert non_admin.get("/api/v1/settings").status_code == 401


def test_api_mutation_requires_admin_session():
    anonymous = TestClient(app)
    res = anonymous.post("/api/v1/data/backfill")
    assert res.status_code == 401


def test_manual_market_refresh_uses_bounded_live_cycle_not_historical_backfill():
    with (
        patch(
            "services.collector.service.IngestionCoordinator.sync_live_cycle",
            new=AsyncMock(return_value={"trade_eligible": True, "instruments_created": 0, "market_rows": 10, "index_rows": 2}),
        ) as live_cycle,
        patch("services.collector.service.IngestionCoordinator.sync_all_data", new=AsyncMock()) as backfill,
        patch("services.collector.service.IngestionCoordinator.run_radar_scan", return_value=[]) as radar_scan,
    ):
        res = client.post("/api/v1/market/sync-all")

    assert res.status_code == 200
    assert res.json()["sync_stats"]["market_rows"] == 10
    live_cycle.assert_awaited_once()
    backfill.assert_not_awaited()
    radar_scan.assert_called_once()


def test_reference_failover_refresh_never_runs_radar_scan_or_trading_gate():
    with (
        patch(
            "services.collector.service.IngestionCoordinator.sync_live_cycle",
            new=AsyncMock(return_value={
                "trade_eligible": False,
                "fallback": True,
                "providers": ["Tindex"],
                "message_fa": "داده جایگزین صرفاً برای نمایش دریافت شد.",
            }),
        ),
        patch("services.collector.service.IngestionCoordinator.run_radar_scan", return_value=[]) as radar_scan,
    ):
        res = client.post("/api/v1/market/sync-all")

    assert res.status_code == 200
    assert res.json()["sync_stats"]["trade_eligible"] is False
    assert "صرفاً برای نمایش" in res.json()["message"]
    radar_scan.assert_not_called()


def test_manual_market_refresh_returns_safe_gateway_timeout():
    with patch(
        "services.collector.service.IngestionCoordinator.sync_live_cycle",
        new=AsyncMock(side_effect=asyncio.TimeoutError),
    ):
        res = client.post("/api/v1/market/sync-all")

    assert res.status_code == 504
    assert "۳۰ ثانیه" in res.json()["detail"]


def test_manual_market_refresh_localizes_provider_failure_without_raw_exception():
    with patch(
        "services.collector.service.IngestionCoordinator.sync_live_cycle",
        new=AsyncMock(side_effect=RuntimeError("sensitive upstream details")),
    ):
        res = client.post("/api/v1/market/sync-all")

    assert res.status_code == 503
    assert "TSETMC" in res.json()["detail"]
    assert "بدون ثبت قیمت یا معامله" in res.json()["detail"]
    assert "sensitive upstream details" not in res.text
