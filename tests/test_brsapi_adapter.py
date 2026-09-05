import httpx
import pytest
from urllib.parse import quote

from packages.data_adapters.brsapi import BrsApiAdapter
from packages.shared.config import settings


class _FakeRateStore:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def ttl(self, key):
        return 5


@pytest.mark.asyncio
async def test_brsapi_full_market_is_contract_checked_and_reference_only(monkeypatch):
    monkeypatch.setattr(settings.brsapi, "enabled", True)
    monkeypatch.setattr(settings.brsapi, "minimum_request_interval_seconds", 0)
    monkeypatch.setattr(settings, "brsapi_api_key", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/Tsetmc/AllSymbols.php"
        assert request.url.params["key"] == "test-key"
        assert request.url.params["type"] == "1"
        assert "Mozilla/5.0" in request.headers["user-agent"]
        return httpx.Response(200, headers={"content-type": "application/json"}, json=[{
            "time": "12:30:01", "l18": "آریا", "l30": "پلیمر آریا ساسول",
            "isin": "IRO3APOZ0001", "id": "1", "py": 1000, "pl": 1010,
            "pc": 1005, "tvol": 1234,
        }])

    adapter = BrsApiAdapter(transport=httpx.MockTransport(handler))
    rows = await adapter.fetch_market_rows()
    assert len(rows) == 1
    assert adapter.independence_key == "BRSAPI_TSETMC_DERIVED"


@pytest.mark.asyncio
async def test_brsapi_price_and_client_type_history_normalize_jalali(monkeypatch):
    monkeypatch.setattr(settings.brsapi, "enabled", True)
    monkeypatch.setattr(settings.brsapi, "minimum_request_interval_seconds", 0)
    monkeypatch.setattr(settings, "brsapi_api_key", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params["type"] == "0":
            payload = [{
                "date": "1405-05-26", "pf": 100, "pmax": 110, "pmin": 99,
                "pc": 105, "pl": 106, "py": 98, "tvol": 1234,
                "tval": 130000, "tno": 20,
            }]
        else:
            payload = [{
                "date": "1405/05/26", "Buy_CountI": 10, "Buy_CountN": 2,
                "Sell_CountI": 8, "Sell_CountN": 1, "Buy_I_Volume": 1000,
                "Buy_N_Volume": 200, "Sell_I_Volume": 900, "Sell_N_Volume": 300,
            }]
        return httpx.Response(200, headers={"content-type": "application/json"}, json=payload)

    price_adapter = BrsApiAdapter(transport=httpx.MockTransport(handler))
    prices = await price_adapter.fetch_eod_history("آریا")
    flow_adapter = BrsApiAdapter(transport=httpx.MockTransport(handler))
    flows = await flow_adapter.fetch_client_type_history("آریا")
    assert prices[0]["trading_date"] == "2026-08-17"
    assert prices[0]["trade_eligible"] is False
    assert flows[0]["trading_date"] == "2026-08-17"
    assert flows[0]["trade_eligible"] is False


@pytest.mark.asyncio
async def test_brsapi_fails_closed_and_redacts_query_key(monkeypatch):
    monkeypatch.setattr(settings.brsapi, "enabled", True)
    monkeypatch.setattr(settings.brsapi, "minimum_request_interval_seconds", 0)
    monkeypatch.setattr(settings, "brsapi_api_key", None)
    adapter = BrsApiAdapter()
    assert await adapter.fetch_market_rows() == []
    assert "not configured" in (adapter.last_error or "")

    secret = "sensitive+/=|test-key"
    monkeypatch.setattr(settings, "brsapi_api_key", secret)

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"blocked {request.url}", request=request)

    adapter = BrsApiAdapter(transport=httpx.MockTransport(handler))
    assert await adapter.fetch_market_rows() == []
    assert secret not in (adapter.last_error or "")
    assert quote(secret, safe="") not in (adapter.last_error or "")
    assert adapter.last_error == "ConnectError"


@pytest.mark.asyncio
async def test_brsapi_rate_limit_is_shared_across_adapter_instances(monkeypatch):
    monkeypatch.setattr(settings.brsapi, "enabled", True)
    monkeypatch.setattr(settings.brsapi, "minimum_request_interval_seconds", 5)
    monkeypatch.setattr(settings, "brsapi_api_key", "test-key")
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, headers={"content-type": "application/json"}, json=[{
            "time": "12:30:01", "l18": "آریا", "l30": "آریا", "isin": "IRO3APOZ0001",
            "id": "1", "py": 1000, "pl": 1010, "pc": 1005, "tvol": 1234,
        }])

    store = _FakeRateStore()
    transport = httpx.MockTransport(handler)
    first = BrsApiAdapter(transport=transport, rate_store=store)
    second = BrsApiAdapter(transport=transport, rate_store=store)
    assert await first.fetch_market_rows()
    assert await second.fetch_market_rows() == []
    assert "LOCAL_RATE_LIMIT" in (second.last_error or "")
    assert calls == 1
