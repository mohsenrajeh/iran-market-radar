"""Official TSETMC authentication contract and safe diagnostics."""
import httpx
import pytest

from packages.data_adapters.tsetmc import TsetmcRestAdapter
from packages.shared.config import settings


@pytest.mark.asyncio
async def test_tsetmc_login_parses_current_nested_error_contract(monkeypatch):
    monkeypatch.setattr(settings, "tsetmc_api_username", "owner")
    monkeypatch.setattr(settings, "tsetmc_api_password", "secret-value")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, json={
            "isSuccess": False,
            "msg": {"msg": "اطلاعات وارد شده نادرست است", "code": -102},
            "data": None,
        })

    adapter = TsetmcRestAdapter()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await adapter._login(client) is False
    assert adapter.last_error_code == -102
    assert "کد -102" in adapter.last_error
    assert "secret-value" not in adapter.last_error


@pytest.mark.asyncio
async def test_tsetmc_login_accepts_lower_camel_success_contract(monkeypatch):
    monkeypatch.setattr(settings, "tsetmc_api_username", "owner")
    monkeypatch.setattr(settings, "tsetmc_api_password", "secret-value")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, json={
            "isSuccess": True,
            "message": "ورود موفق",
            "data": {"token": "jwt-value", "expireDate": "2026-08-17T12:30:00Z"},
        })

    adapter = TsetmcRestAdapter()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await adapter._login(client) is True
    assert adapter._token == "jwt-value"
    assert adapter.last_error is None
    assert adapter.last_error_code is None
