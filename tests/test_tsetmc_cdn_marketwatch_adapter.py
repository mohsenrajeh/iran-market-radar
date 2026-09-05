from datetime import datetime, timezone
from email.utils import format_datetime

import httpx
import pytest

from packages.data_adapters.tsetmc_cdn_marketwatch import TsetmcCdnMarketWatchAdapter


@pytest.mark.asyncio
async def test_cdn_marketwatch_uses_body_clock_and_numeric_official_identity():
    response_at = datetime(2026, 8, 17, 9, 29, 30, tzinfo=timezone.utc)

    async def handler(request: httpx.Request) -> httpx.Response:
        assert "Mozilla/5.0" in request.headers["user-agent"]
        return httpx.Response(200, headers={
            "content-type": "application/json",
            "date": format_datetime(response_at, usegmt=True),
        }, json={"marketwatch": [{
            "insID": "IRO3ASPZ0001", "insCode": "46348559193224090",
            "lva": "فولاد", "lvc": "فولاد مبارکه اصفهان",
            "dEven": 0, "hEven": 125900,
            "pdv": 20930, "pcl": 20910, "py": 20330, "pf": 20400,
            "pmn": 20350, "pmx": 20930, "qtj": 1200, "qtc": 25000000, "ztt": 42,
            "pMin": 19730, "pMax": 20930,
        }]})

    rows = await TsetmcCdnMarketWatchAdapter(transport=httpx.MockTransport(handler)).fetch_rows()
    assert rows[0]["isin"] == "IRO3ASPZ0001"
    assert rows[0]["source_instrument_code"] == "46348559193224090"
    assert rows[0]["observed_at"] == datetime(2026, 8, 17, 9, 29, 0, tzinfo=timezone.utc)
    assert rows[0]["last"] == 20930


@pytest.mark.asyncio
async def test_cdn_marketwatch_rejects_future_or_non_numeric_identity():
    response_at = datetime(2026, 8, 17, 9, 0, 0, tzinfo=timezone.utc)
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={
            "content-type": "application/json", "date": format_datetime(response_at, usegmt=True),
        }, json={"marketwatch": [{
            "insID": "IRO3ASPZ0001", "insCode": "bad", "hEven": 130000,
            "lva": "فولاد", "lvc": "فولاد مبارکه اصفهان",
            "pdv": 1, "pcl": 1, "py": 1, "pf": 1, "pmn": 1, "pmx": 1,
            "qtj": 1, "qtc": 1, "ztt": 1, "pMin": 1, "pMax": 1,
        }]})
    adapter = TsetmcCdnMarketWatchAdapter(transport=httpx.MockTransport(handler))
    assert await adapter.fetch_rows() == []
    assert adapter.last_error
