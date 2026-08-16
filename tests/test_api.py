"""Integration tests for FastAPI endpoints."""
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.shared.database import init_db_sync

init_db_sync()
client = TestClient(app)


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
    assert len(data["indices"]) > 0


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
