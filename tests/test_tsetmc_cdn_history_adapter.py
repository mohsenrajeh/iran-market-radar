import json

import httpx
import pytest

from packages.data_adapters.tsetmc_cdn_history import TsetmcCdnHistoryAdapter


INS_CODE = "46348559193224090"


def _eod_row() -> dict:
    return {
        "priceChange": 66.0,
        "priceMin": 2182.0,
        "priceMax": 2285.0,
        "priceYesterday": 2219.0,
        "priceFirst": 2188.0,
        "last": False,
        "id": 0,
        "insCode": INS_CODE,
        "dEven": 20260816,
        "hEven": 115534,
        "pClosing": 2274.0,
        "iClose": False,
        "yClose": True,
        "pDrCotVal": 2285.0,
        "zTotTran": 21901.0,
        "qTotTran5J": 3610329576.0,
        "qTotCap": 8209431045219.0,
    }


def _client_type_row() -> dict:
    return {
        "recDate": 20260816,
        "insCode": INS_CODE,
        "buy_I_Volume": 3423365931.0,
        "buy_N_Volume": 186963645.0,
        "buy_I_Value": 7783379991613.0,
        "buy_N_Value": 426051053606.0,
        "buy_N_Count": 22,
        "sell_I_Volume": 1262706512.0,
        "buy_I_Count": 6300.0,
        "sell_N_Volume": 2347623064.0,
        "sell_I_Value": 2865739334885.0,
        "sell_N_Value": 5343691710334.0,
        "sell_N_Count": 47,
        "sell_I_Count": 3502,
    }


@pytest.mark.asyncio
async def test_cdn_history_normalizes_price_and_client_type_contracts():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert "Mozilla/5.0" in request.headers["user-agent"]
        if request.url.path.endswith(f"/ClosingPrice/GetClosingPriceDailyList/{INS_CODE}/0"):
            payload = {"closingPriceDaily": [_eod_row()]}
        else:
            assert request.url.path.endswith(f"/ClientType/GetClientTypeHistory/{INS_CODE}")
            payload = {"clientType": [_client_type_row()]}
        return httpx.Response(200, headers={"content-type": "application/json"}, json=payload)

    transport = httpx.MockTransport(handler)
    eod = await TsetmcCdnHistoryAdapter(transport=transport).fetch_eod_history(INS_CODE)
    flows = await TsetmcCdnHistoryAdapter(transport=transport).fetch_client_type_history(INS_CODE)

    assert eod == [{
        "source_instrument_code": INS_CODE,
        "trading_date": "2026-08-16",
        "open": 2188.0,
        "high": 2285.0,
        "low": 2182.0,
        "close": 2274.0,
        "last": 2285.0,
        "yesterday_price": 2219.0,
        "volume": 3610329576,
        "value": 8209431045219.0,
        "trade_count": 21901,
        "allowed_min": None,
        "allowed_max": None,
        "source": "TSETMC_PUBLIC_CDN",
        "trade_eligible": False,
    }]
    assert flows == [{
        "source_instrument_code": INS_CODE,
        "trading_date": "2026-08-16",
        "real_buy_count": 6300,
        "real_buy_volume": 3423365931,
        "real_buy_value": 7783379991613.0,
        "real_sell_count": 3502,
        "real_sell_volume": 1262706512,
        "real_sell_value": 2865739334885.0,
        "legal_buy_count": 22,
        "legal_buy_volume": 186963645,
        "legal_buy_value": 426051053606.0,
        "legal_sell_count": 47,
        "legal_sell_volume": 2347623064,
        "legal_sell_value": 5343691710334.0,
        "source": "TSETMC_PUBLIC_CDN",
        "trade_eligible": False,
    }]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("root", "row_update", "expected_fragment"),
    [
        ("wrongRoot", {}, "root contract"),
        ("closingPriceDaily", {"insCode": "999"}, "row validation"),
        ("closingPriceDaily", {"dEven": 20260230}, "row validation"),
        ("closingPriceDaily", {"pClosing": 0}, "row validation"),
        ("closingPriceDaily", {"priceMax": 2100}, "row validation"),
    ],
)
async def test_cdn_eod_history_fails_closed_on_schema_identity_date_or_price(root, row_update, expected_fragment):
    row = {**_eod_row(), **row_update}

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, json={root: [row]})

    adapter = TsetmcCdnHistoryAdapter(transport=httpx.MockTransport(handler))
    assert await adapter.fetch_eod_history(INS_CODE) == []
    assert expected_fragment in (adapter.last_error or "")


@pytest.mark.asyncio
async def test_cdn_client_type_fails_closed_on_one_identity_mismatch():
    rows = [_client_type_row(), {**_client_type_row(), "insCode": "999"}]

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, json={"clientType": rows})

    adapter = TsetmcCdnHistoryAdapter(transport=httpx.MockTransport(handler))
    assert await adapter.fetch_client_type_history(INS_CODE) == []
    assert adapter.last_error == "TSETMC CDN client-type history failed row validation."


@pytest.mark.asyncio
async def test_cdn_eod_skips_documented_no_trade_calendar_rows():
    no_trade = {
        **_eod_row(),
        "dEven": 20260815,
        "priceFirst": 1718,
        "priceMin": 0,
        "priceMax": 0,
        "pClosing": 2274,
        "pDrCotVal": 2274,
        "priceYesterday": 2274,
        "qTotTran5J": 0,
        "qTotCap": 0,
        "zTotTran": 0,
    }

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"closingPriceDaily": [no_trade, _eod_row()]},
        )

    adapter = TsetmcCdnHistoryAdapter(transport=httpx.MockTransport(handler))
    rows = await adapter.fetch_eod_history(INS_CODE, days=1)
    assert len(rows) == 1
    assert rows[0]["trading_date"] == "2026-08-16"
    assert adapter.last_error is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content_type", "body", "expected"),
    [
        ("text/html", b"<html></html>", "non-JSON"),
        ("application/json", b"not-json", "JSONDecodeError"),
        ("application/json", json.dumps([_eod_row()]).encode(), "root contract"),
    ],
)
async def test_cdn_history_rejects_non_json_and_invalid_root(content_type, body, expected):
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": content_type}, content=body)

    adapter = TsetmcCdnHistoryAdapter(transport=httpx.MockTransport(handler))
    assert await adapter.fetch_eod_history(INS_CODE) == []
    assert expected in (adapter.last_error or "")


@pytest.mark.asyncio
async def test_cdn_history_enforces_streamed_response_limit():
    body = json.dumps({"closingPriceDaily": [_eod_row()]}).encode()

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, content=body)

    adapter = TsetmcCdnHistoryAdapter(
        transport=httpx.MockTransport(handler),
        max_response_bytes=16,
    )
    assert await adapter.fetch_eod_history(INS_CODE) == []
    assert "size limit" in (adapter.last_error or "")


@pytest.mark.asyncio
async def test_cdn_history_rejects_bad_request_parameters_without_network():
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    adapter = TsetmcCdnHistoryAdapter(transport=httpx.MockTransport(handler))
    assert await adapter.fetch_eod_history("not-an-inscode") == []
    assert await adapter.fetch_client_type_history(INS_CODE, days=0) == []
    assert calls == 0
