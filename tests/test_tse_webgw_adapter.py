from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest

from packages.data_adapters.tse_webgw import TseWebGwAdapter


def _valid_row() -> dict:
    return {
        "instrumentId": "IRO3ASPZ0001",
        "instrumentName": "آ س پ",
        "companyNamePersian": "آ.س.پ",
        "tradeVolume": {"value": 5_059_177, "state": 0},
        "tradeValue": {"value": 105_793_384_410, "state": 0},
        "tradeCount": {"value": 476, "state": 0},
        "highValue": {"value": 20_930, "state": 0},
        "lowValue": {"value": 20_800, "state": 0},
        "minValue": 19_730,
        "maxValue": 20_930,
        "lastPrice": {"value": 20_930, "state": 0},
        "closingPrice": {"value": 20_910, "state": 0},
        "yesterdayPrice": {"value": 20_330, "state": 0},
        "firstPrice": {"value": 20_900, "state": 0},
        "pe": {"value": 20.42, "state": 0},
        "eps": {"value": 1024.0, "state": 0},
        "marketValue": {"value": 20_930_000_000_000, "state": 0},
        "statename": "مجاز",
        "marketname": "فرابورس",
    }


@pytest.mark.asyncio
async def test_webgw_valid_payload_is_normalized_with_exact_batch_clock():
    batch_clock = datetime(2026, 8, 17, 9, 18, 48, tzinfo=timezone.utc)

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/MarketWatch/MarketWatchCash/fa")
        assert "Mozilla/5.0" in request.headers["user-agent"]
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"Items": [_valid_row()]},
        )

    adapter = TseWebGwAdapter(transport=httpx.MockTransport(handler))
    rows = await adapter.fetch_market_rows(batch_clock=batch_clock)

    assert rows == [{
        "source_instrument_code": "IRO3ASPZ0001",
        "isin": "IRO3ASPZ0001",
        "ticker": "ا س پ",
        "ticker_normalized": "ا س پ",
        "name_fa": "ا.س.پ",
        "open": 20_900.0,
        "high": 20_930.0,
        "low": 20_800.0,
        "last": 20_930.0,
        "close": 20_910.0,
        "yesterday_price": 20_330.0,
        "volume": 5_059_177,
        "value": 105_793_384_410.0,
        "trade_count": 476,
        "allowed_min": 19_730.0,
        "allowed_max": 20_930.0,
        "pe": 20.42,
        "eps": 1024.0,
        "market_value": 20_930_000_000_000.0,
        "state": "مجاز",
        "market": "فرابورس",
        "observed_at": batch_clock.isoformat(),
        "source": "TSE_WEBGW",
    }]
    assert adapter.last_error is None
    assert adapter.rejected_row_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"items": [_valid_row()]},
        {"Items": []},
        {"Items": [{**_valid_row(), "instrumentId": "not-an-isin"}]},
        {"Items": [{**_valid_row(), "lastPrice": {"value": 0}}]},
        {"Items": [{**_valid_row(), "minValue": 30_000, "maxValue": 20_000}]},
    ],
)
async def test_webgw_missing_or_invalid_contract_fails_closed(payload):
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, json=payload)

    adapter = TseWebGwAdapter(transport=httpx.MockTransport(handler))
    rows = await adapter.fetch_market_rows(batch_clock=datetime.now(timezone.utc))

    assert rows == []
    assert adapter.last_error


@pytest.mark.asyncio
async def test_webgw_explicit_timestamp_must_be_timezone_aware():
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"Items": [_valid_row()]})

    adapter = TseWebGwAdapter(transport=httpx.MockTransport(handler))
    assert await adapter.fetch_market_rows(batch_clock=datetime(2026, 8, 17, 9, 18, 48)) == []
    assert adapter.last_error == "WebGW batch clock is missing or timezone-naive."
    assert calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("clock_offset", "expected_error"),
    [
        (None, "TSE WebGW HTTP Date is missing or invalid."),
        (timedelta(minutes=-5), "TSE WebGW HTTP Date is stale."),
        (timedelta(minutes=5), "TSE WebGW HTTP Date is in the future."),
    ],
)
async def test_webgw_http_date_missing_stale_or_future_fails_closed(clock_offset, expected_error):
    async def handler(_request: httpx.Request) -> httpx.Response:
        headers = {"content-type": "application/json"}
        # Compute the response clock when the handler actually runs. Building a
        # future timestamp during pytest collection becomes flaky in a long suite.
        if clock_offset is not None:
            headers["date"] = format_datetime(datetime.now(timezone.utc) + clock_offset, usegmt=True)
        return httpx.Response(200, headers=headers, json={"Items": [_valid_row()]})

    adapter = TseWebGwAdapter(
        transport=httpx.MockTransport(handler),
        max_response_age_seconds=60,
        max_future_skew_seconds=30,
    )
    assert await adapter.fetch_market_rows() == []
    assert adapter.last_error == expected_error
    assert adapter.last_response_at is None


@pytest.mark.asyncio
async def test_webgw_uses_fresh_aware_http_date_as_batch_clock():
    response_at = datetime.now(timezone.utc).replace(microsecond=0)

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "application/json",
                "date": format_datetime(response_at, usegmt=True),
                "cache-control": "no-store",
            },
            json={"Items": [_valid_row()]},
        )

    adapter = TseWebGwAdapter(transport=httpx.MockTransport(handler))
    rows = await adapter.fetch_market_rows()
    assert rows[0]["observed_at"] == response_at.isoformat()
    assert adapter.last_response_at == response_at
