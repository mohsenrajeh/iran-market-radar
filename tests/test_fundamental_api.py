"""Tests for Fundamental Analysis and Codal API Endpoints."""
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_fundamental_symbols(client):
    """Verify GET /api/v1/fundamentals/symbols returns list of symbols with fundamental scores."""
    resp = client.get("/api/v1/fundamentals/symbols")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0

    first = data[0]
    assert "symbol" in first
    assert "p_e_ratio" in first
    assert "roe_pct" in first
    assert "piotroski_f_score" in first
    assert "fundamental_score" in first
    assert "fundamental_grade" in first
    assert "valuation_status_fa" in first


def test_get_codal_feed(client):
    """Verify GET /api/v1/fundamentals/codal-feed returns parsed filings."""
    resp = client.get("/api/v1/fundamentals/codal-feed")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0

    first = data[0]
    assert "title" in first
    assert "filing_type_fa" in first
    assert "sentiment" in first
    assert "summary_fa" in first


def test_get_macro_dashboard(client):
    """Verify GET /api/v1/fundamentals/macro returns NIMA rate and commodities."""
    resp = client.get("/api/v1/fundamentals/macro")
    assert resp.status_code == 200
    data = resp.json()

    assert "nima_usd_rate" in data
    assert data["nima_usd_rate"] > 0
    assert "commodities" in data
    assert len(data["commodities"]) >= 4
    assert "last_updated_jalali" in data
