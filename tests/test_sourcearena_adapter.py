import httpx
import pytest

from packages.data_adapters.sourcearena import SourceArenaAdapter
from packages.shared.config import settings


@pytest.mark.asyncio
async def test_sourcearena_history_is_normalized_but_not_trade_eligible(monkeypatch):
    monkeypatch.setattr(settings.sourcearena, "enabled", True)
    monkeypatch.setattr(settings, "sourcearena_api_token", "test-token")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/"
        assert request.url.params["token"] == "test-token"
        assert request.url.params["name"] == "فملی"
        return httpx.Response(200, json=[{
            "date": "1405/05/26", "first_price": "100", "close_price": "104",
            "highest_price": "106", "lowest_price": "99", "trade_volume": 1234,
        }])

    adapter = SourceArenaAdapter(transport=httpx.MockTransport(handler))
    rows = await adapter.fetch_eod_history("فملی", days=260)
    assert len(rows) == 1
    assert rows[0]["trading_date"] == "2026-08-17"
    assert rows[0]["allowed_min"] is None
    assert rows[0]["trade_eligible"] is False


@pytest.mark.asyncio
async def test_sourcearena_fails_closed_without_token(monkeypatch):
    monkeypatch.setattr(settings.sourcearena, "enabled", True)
    monkeypatch.setattr(settings, "sourcearena_api_token", None)
    adapter = SourceArenaAdapter()
    assert await adapter.fetch_market_rows() == []
    assert "not configured" in (adapter.last_error or "")


@pytest.mark.asyncio
async def test_sourcearena_redacts_query_token_from_transport_errors(monkeypatch):
    secret = "sensitive-test-token"
    monkeypatch.setattr(settings.sourcearena, "enabled", True)
    monkeypatch.setattr(settings, "sourcearena_api_token", secret)

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"blocked {request.url}", request=request)

    adapter = SourceArenaAdapter(transport=httpx.MockTransport(handler))
    assert await adapter.fetch_market_rows() == []
    assert secret not in (adapter.last_error or "")
