"""Tests for automated paper trading, attribution system, and auto-trading endpoints."""
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.domain.models import Portfolio, Position, PaperTradeLog, IndicatorPerformance
from packages.shared.database import init_db_sync, SyncSessionLocal
from services.paper_broker.auto_trader import auto_trader
from services.paper_broker.attribution import update_indicator_attribution, INDICATOR_DEFINITIONS


@pytest.fixture(scope="module")
def client():
    init_db_sync()
    with TestClient(app) as c:
        yield c


def test_auto_trader_status_api(client):
    res = client.get("/api/v1/auto-trading/status")
    assert res.status_code == 200
    data = res.json()
    assert "is_running" in data
    assert "total_cycles" in data
    assert "total_trades" in data


def test_auto_trader_portfolio_history_api(client):
    res = client.get("/api/v1/auto-trading/portfolio-history")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_auto_trader_trade_log_api(client):
    res = client.get("/api/v1/auto-trading/trade-log")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        first = data[0]
        assert "symbol" in first
        assert "entry_price" in first
        assert "total_invested_tomans" in first
        assert "risk_pct" in first
        assert "risk_reward_ratio" in first
        assert "decision_method" in first


def test_auto_trader_attribution_api(client):
    res = client.get("/api/v1/auto-trading/attribution")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_indicator_attribution_update():
    db = SyncSessionLocal()
    try:
        trade = PaperTradeLog(
            portfolio_id="port_default_paper",
            symbol="فولاد",
            side="BUY",
            entry_price=10000.0,
            exit_price=11000.0,
            quantity=1000,
            gross_pnl=1000000.0,
            net_pnl=950000.0,
            return_pct=9.5,
            features_at_entry={
                "rsi_14": 55.0,
                "supertrend_direction": 1.0,
                "real_buyer_power_ratio": 1.4,
                "ema_trend_score": 0.8,
            },
            is_closed=True,
        )
        db.add(trade)
        db.flush()

        update_indicator_attribution(db, trade)
        db.commit()

        assert "rsi_14" in trade.indicator_scores
        assert trade.indicator_scores["rsi_14"] == 1.0
        assert trade.indicator_scores["supertrend"] == 1.0

        perf = db.query(IndicatorPerformance).filter(IndicatorPerformance.indicator_name == "rsi_14").first()
        assert perf is not None
        assert perf.total_signals >= 1
    finally:
        db.close()
