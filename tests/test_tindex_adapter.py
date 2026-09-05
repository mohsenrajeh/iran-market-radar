import json

import httpx
import pytest

from packages.data_adapters.tindex import TindexAdapter
from packages.shared.config import settings
from packages.data_adapters.source_registry import load_source_registry


class _FakeRateStore:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, *, ex=None, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.ttls[key] = ex
        return True

    async def ttl(self, key):
        return self.ttls.get(key, -1)

    async def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    async def decr(self, key):
        self.values[key] = int(self.values.get(key, 0)) - 1
        return self.values[key]

    async def delete(self, key):
        self.values.pop(key, None)
        self.ttls.pop(key, None)
        return 1

    async def expire(self, key, seconds):
        self.ttls[key] = seconds
        return True


@pytest.mark.asyncio
async def test_tindex_market_overview_uses_documented_envelope(monkeypatch):
    monkeypatch.setattr(settings.tindex, "enabled", True)
    monkeypatch.setattr(settings, "tindex_api_token", "test-token")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-token"
        assert request.url.path == "/api/public/stock-market/overview"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=json.dumps({"success": True, "data": {"as_of": "2026-08-17", "indices": []}}).encode(),
        )

    adapter = TindexAdapter(transport=httpx.MockTransport(handler))
    result = await adapter.fetch_market_overview()
    assert result == {"as_of": "2026-08-17", "indices": []}
    assert adapter.last_error is None


@pytest.mark.asyncio
async def test_tindex_stock_page_preserves_documented_pagination_meta(monkeypatch):
    monkeypatch.setattr(settings.tindex, "enabled", True)
    monkeypatch.setattr(settings, "tindex_api_token", "test-token")
    monkeypatch.setattr(settings.tindex, "minimum_request_interval_seconds", 0)

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["page"] == "2"
        assert request.url.params["per_page"] == "100"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "success": True,
                "data": {"rows": [{"slug": "stock-1", "ticker": "فولاد", "last_price": 1234}]},
                "meta": {"page": 2, "per_page": 100, "total": 1644, "has_more": True, "last_page": 17},
            },
        )

    adapter = TindexAdapter(transport=httpx.MockTransport(handler))
    page = await adapter.fetch_stock_page_envelope(page=2, per_page=100)
    assert page is not None
    assert page["rows"][0]["ticker"] == "فولاد"
    assert page["meta"] == {"page": 2, "per_page": 100, "total": 1644, "has_more": True, "last_page": 17}


@pytest.mark.asyncio
async def test_tindex_candle_delta_dates_are_decoded(monkeypatch):
    monkeypatch.setattr(settings.tindex, "enabled", True)
    monkeypatch.setattr(settings, "tindex_api_token", "test-token")
    monkeypatch.setattr(settings.tindex, "minimum_request_interval_seconds", 0)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "success": True,
                "data": {
                    "t": [20000, 1], "o": [100, 101], "h": [105, 106],
                    "l": [99, 100], "c": [104, 105], "partial": [False, True],
                },
            },
        )

    adapter = TindexAdapter(transport=httpx.MockTransport(handler))
    candles = await adapter.fetch_symbol_candles("فولاد")
    assert len(candles) == 2
    assert candles[1]["trading_date"] > candles[0]["trading_date"]
    assert candles[1]["partial"] is True


@pytest.mark.asyncio
async def test_tindex_fails_closed_when_disabled(monkeypatch):
    monkeypatch.setattr(settings.tindex, "enabled", False)
    adapter = TindexAdapter()
    assert await adapter.fetch_market_overview() is None
    assert adapter.last_error == "Tindex adapter is disabled."


def test_provider_catalog_never_exposes_credentials():
    catalog = load_source_registry()
    serialized = json.dumps(catalog, ensure_ascii=False)
    assert "password" not in serialized.lower()
    for secret in (
        settings.tsetmc_api_password,
        settings.tindex_api_token,
        settings.bourseview_api_token,
        settings.sourcearena_api_token,
        settings.brsapi_api_key,
    ):
        if secret:
            assert secret not in serialized
    assert "tsetmc_authenticated_api" in serialized
    assert "tindex_secondary" in serialized
    assert "bourseview_commercial" in serialized
    assert "brsapi_market_api" in serialized


@pytest.mark.asyncio
async def test_tindex_rate_limit_is_shared_across_adapter_instances(monkeypatch):
    monkeypatch.setattr(settings.tindex, "enabled", True)
    monkeypatch.setattr(settings, "tindex_api_token", "test-token")
    monkeypatch.setattr(settings.tindex, "minimum_request_interval_seconds", 60)
    monkeypatch.setattr(settings.tindex, "daily_success_limit", 100)
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, headers={"content-type": "application/json"}, json={"success": True, "data": {"as_of": "2026-08-17", "indices": []}})

    store = _FakeRateStore()
    transport = httpx.MockTransport(handler)
    first = TindexAdapter(transport=transport, rate_store=store)
    second = TindexAdapter(transport=transport, rate_store=store)

    assert await first.fetch_market_overview() is not None
    assert await second.fetch_market_overview() is None
    assert calls == 1
    assert second.last_error.startswith("LOCAL_RATE_LIMIT")


@pytest.mark.asyncio
async def test_tindex_conservative_daily_allowance_blocks_before_network(monkeypatch):
    monkeypatch.setattr(settings.tindex, "enabled", True)
    monkeypatch.setattr(settings, "tindex_api_token", "test-token")
    monkeypatch.setattr(settings.tindex, "minimum_request_interval_seconds", 60)
    monkeypatch.setattr(settings.tindex, "daily_success_limit", 2)
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, headers={"content-type": "application/json"}, json={"success": True, "data": {"as_of": "2026-08-17", "indices": []}})

    store = _FakeRateStore()
    transport = httpx.MockTransport(handler)
    for _ in range(2):
        adapter = TindexAdapter(transport=transport, rate_store=store)
        assert await adapter.fetch_market_overview() is not None
        await store.delete("iran-market-radar:tindex:request-window")

    blocked = TindexAdapter(transport=transport, rate_store=store)
    assert await blocked.fetch_market_overview() is None
    assert blocked.last_error.startswith("LOCAL_DAILY_LIMIT")
    assert calls == 2
