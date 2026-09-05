"""Direct, credential-free adapter for the official TSETMC public CDN JSON API.

This is the canonical intraday provider. It never scrapes HTML, never invents
prices, and preserves the provider body clock (``hEven``) for every row.
"""
from __future__ import annotations

import asyncio
import json
import math
import re
from datetime import datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, TypedDict
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from packages.shared.config import settings
from packages.shared.persian import normalize_persian_text, normalize_ticker

TEHRAN = ZoneInfo("Asia/Tehran")
_ISIN = re.compile(r"^IR[A-Z0-9]{10}$")
_TRANSIENT = {408, 425, 500, 502, 503, 504}
_BLOCK_STATUSES = {403, 429}
_BLOCK_MARKERS = (
    "مسدود", "دسترسی شما", "general error detected", "request rejected",
    "access denied", "too many requests", "cloudflare",
)


class CdnMarketRow(TypedDict):
    source_instrument_code: str
    isin: str
    ticker: str
    ticker_normalized: str
    name_fa: str
    market: str
    open: float
    high: float
    low: float
    last: float
    close: float
    yesterday_price: float
    volume: int
    value: float
    trade_count: int
    allowed_min: float
    allowed_max: float
    pe: float | None
    eps: float | None
    market_value: float | None
    state: str
    trade_eligible: bool
    observed_at: datetime
    source: str


CdnMarketClockRow = CdnMarketRow


class TsetmcCdnMarketWatchAdapter:
    provider_name = "TSETMC Public CDN"
    independence_key = "TSETMC_OFFICIAL_PUBLIC_CDN"
    default_base_url = "https://cdn.tsetmc.com"
    market_watch_path = (
        "/api/ClosingPrice/GetMarketWatch?market=0"
        "&paperTypes%5B0%5D=1&paperTypes%5B1%5D=2&paperTypes%5B2%5D=3"
        "&paperTypes%5B3%5D=4&paperTypes%5B4%5D=5&paperTypes%5B5%5D=6"
        "&paperTypes%5B6%5D=7&paperTypes%5B7%5D=8&paperTypes%5B8%5D=9"
        "&withBestLimits=false&hEven=0&RefID=0"
    )
    browser_user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None,
                 base_url: str | None = None, timeout_seconds: float | None = None,
                 retry_attempts: int | None = None) -> None:
        self.transport = transport
        self.base_url = (base_url or self.default_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds or max(10, settings.tsetmc.request_timeout_seconds)
        self.retry_attempts = retry_attempts if retry_attempts is not None else settings.tsetmc.retry_attempts
        self.last_error: str | None = None
        self.last_response_at: datetime | None = None
        self.rejected_row_count = 0
        self.raw_row_count = 0
        self.last_failure_kind: str | None = None
        self.transport_clock_source: str | None = None

    @staticmethod
    def _number(row: dict[str, Any], *keys: str, positive: bool = False) -> float:
        for key in keys:
            raw = row.get(key)
            if raw is None or isinstance(raw, bool):
                continue
            value = float(raw)
            if math.isfinite(value) and (value > 0 if positive else value >= 0):
                return value
        raise ValueError(keys[0])

    @classmethod
    def _optional_number(cls, row: dict[str, Any], *keys: str) -> float | None:
        try:
            return cls._number(row, *keys)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _integer(value: float, key: str) -> int:
        if not value.is_integer():
            raise ValueError(key)
        return int(value)

    @staticmethod
    def _row_clock(row: dict[str, Any], response_at: datetime) -> datetime:
        raw = str(row.get("hEven") or "").zfill(6)
        if len(raw) != 6 or not raw.isdigit():
            raise ValueError("hEven")
        hh, mm, ss = int(raw[:2]), int(raw[2:4]), int(raw[4:])
        local_date = response_at.astimezone(TEHRAN).date()
        d_even = str(row.get("dEven") or "")
        if len(d_even) == 8 and d_even.isdigit() and d_even != "00000000":
            local_date = datetime.strptime(d_even, "%Y%m%d").date()
        observed = datetime.combine(local_date, time(hh, mm, ss), tzinfo=TEHRAN).astimezone(timezone.utc)
        if observed > response_at + timedelta(minutes=2):
            raise ValueError("future hEven")
        return observed

    async def _request_json(self, path: str) -> tuple[dict[str, Any] | list[Any] | None, datetime | None]:
        headers = {
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "DNT": "1",
            "Origin": "https://www.tsetmc.com",
            "Referer": "https://www.tsetmc.com/",
            "User-Agent": self.browser_user_agent,
        }
        attempts = max(1, self.retry_attempts + 1)
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url, timeout=self.timeout_seconds,
                    follow_redirects=False, transport=self.transport,
                    proxy=(settings.data_http_proxy or None) if self.transport is None else None,
                    trust_env=settings.data_http_trust_env, headers=headers,
                ) as client:
                    async with client.stream("GET", path) as response:
                        content_type = response.headers.get("content-type", "").lower()
                        if response.status_code in _BLOCK_STATUSES:
                            body = (await response.aread())[:65_536].decode("utf-8", errors="ignore").lower()
                            self.last_failure_kind = "blocked"
                            self.last_error = f"TSETMC CDN access blocked (HTTP {response.status_code})."
                            return None, None
                        if response.status_code in _TRANSIENT and attempt + 1 < attempts:
                            await response.aread()
                            await asyncio.sleep(settings.tsetmc.backoff_initial_seconds * (2 ** attempt))
                            continue
                        if response.status_code != 200:
                            self.last_failure_kind = "http"
                            self.last_error = f"TSETMC CDN HTTP {response.status_code}."
                            return None, None
                        if "json" not in content_type:
                            body = (await response.aread())[:65_536].decode("utf-8", errors="ignore").lower()
                            blocked = any(marker in body for marker in _BLOCK_MARKERS)
                            self.last_failure_kind = "blocked" if blocked else "schema"
                            self.last_error = (
                                "TSETMC CDN returned a soft-block response."
                                if blocked else "TSETMC CDN returned HTML or non-JSON content."
                            )
                            return None, None
                        # Quote freshness comes from each row's official
                        # dEven/hEven body clock.  HTTP Date is only a
                        # transport-receipt bound and is not guaranteed to be
                        # present or normalized by every CDN edge.
                        response_at = datetime.now(timezone.utc)
                        self.transport_clock_source = "local_receive_fallback"
                        raw_http_date = response.headers.get("date")
                        if raw_http_date:
                            try:
                                parsed_http_date = parsedate_to_datetime(raw_http_date)
                                if parsed_http_date.tzinfo is not None:
                                    response_at = parsed_http_date.astimezone(timezone.utc)
                                    self.transport_clock_source = "http_date"
                            except (TypeError, ValueError, OverflowError):
                                pass
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > settings.tsetmc.max_response_bytes:
                                self.last_error = "TSETMC CDN response exceeded size limit."
                                return None, None
                payload = json.loads(body)
                if not isinstance(payload, (dict, list)):
                    self.last_failure_kind = "schema"
                    self.last_error = "TSETMC CDN root contract failed."
                    return None, None
                return payload, response_at
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError,
                    httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.PoolTimeout) as exc:
                if attempt + 1 >= attempts:
                    self.last_failure_kind = "network"
                    self.last_error = type(exc).__name__
                    return None, None
                await asyncio.sleep(settings.tsetmc.backoff_initial_seconds * (2 ** attempt))
            except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError, OverflowError) as exc:
                self.last_failure_kind = "schema"
                self.last_error = type(exc).__name__
                return None, None
        return None, None

    @classmethod
    def _normalize_row(cls, row: dict[str, Any], response_at: datetime) -> CdnMarketRow:
        isin = str(row.get("insID") or "").strip().upper()
        code = str(row.get("insCode") or "").strip()
        ticker = normalize_persian_text(str(row.get("lva") or "").strip())
        name = normalize_persian_text(str(row.get("lvc") or "").strip())
        if not _ISIN.fullmatch(isin) or not code.isdigit() or not ticker or not name:
            raise ValueError("identity")
        if not isin.startswith(("IRO1", "IRO3")):
            raise ValueError("non-equity paper family")
        last = cls._number(row, "pdv", "pDrCotVal", positive=True)
        close = cls._number(row, "pcl", "pClosing", positive=True)
        yesterday = cls._number(row, "py", "priceYesterday", positive=True)
        low = cls._number(row, "pmn")
        high = cls._number(row, "pmx")
        allowed_min = cls._number(row, "pMin", positive=True)
        allowed_max = cls._number(row, "pMax", positive=True)
        if high < low or allowed_max < allowed_min:
            raise ValueError("price range")
        return CdnMarketRow(
            source_instrument_code=code, isin=isin, ticker=ticker,
            ticker_normalized=normalize_ticker(ticker), name_fa=name,
            market="TSE" if isin.startswith("IRO1") else "IFB",
            open=cls._number(row, "pf"), high=high, low=low,
            last=last, close=close, yesterday_price=yesterday,
            volume=cls._integer(cls._number(row, "qtj", "qTotTran5J"), "volume"),
            value=cls._number(row, "qtc", "qTotCap"),
            trade_count=cls._integer(cls._number(row, "ztt", "zTotTran"), "trade_count"),
            allowed_min=allowed_min, allowed_max=allowed_max,
            pe=cls._optional_number(row, "pe"), eps=cls._optional_number(row, "eps"),
            market_value=cls._optional_number(row, "bv"),
            state=str(row.get("csv") or "UNKNOWN").strip() or "UNKNOWN",
            trade_eligible=bool(cls._number(row, "pf") > 0 and high > 0 and low > 0),
            observed_at=cls._row_clock(row, response_at), source="TSETMC_PUBLIC_CDN",
        )

    async def fetch_market_rows(self) -> list[CdnMarketRow]:
        self.last_error = None
        self.last_failure_kind = None
        self.transport_clock_source = None
        self.last_response_at = None
        self.rejected_row_count = 0
        payload, response_at = await self._request_json(self.market_watch_path)
        raw_rows = payload.get("marketwatch") if isinstance(payload, dict) else None
        if not isinstance(raw_rows, list) or not raw_rows or response_at is None:
            self.last_error = self.last_error or "TSETMC CDN market-watch root contract failed."
            return []
        self.raw_row_count = len(raw_rows)
        rows: list[CdnMarketRow] = []
        seen: set[str] = set()
        for raw in raw_rows:
            if not isinstance(raw, dict):
                self.rejected_row_count += 1
                continue
            raw_isin = str(raw.get("insID") or "").strip().upper()
            if not raw_isin.startswith(("IRO1", "IRO3")):
                continue
            try:
                row = self._normalize_row(raw, response_at)
                if row["isin"] in seen:
                    raise ValueError("duplicate identity")
                seen.add(row["isin"])
                rows.append(row)
            except (TypeError, ValueError, OverflowError):
                self.rejected_row_count += 1
        if not rows:
            self.last_error = "TSETMC CDN market-watch contained no valid equity rows."
            return []
        self.last_response_at = response_at
        return rows

    async def fetch_rows(self) -> list[CdnMarketRow]:
        return await self.fetch_market_rows()

    async def fetch_closing_price_info(self, ins_code: str) -> dict[str, Any] | None:
        if not str(ins_code).isdigit():
            self.last_error = "Invalid InsCode."
            return None
        payload, _ = await self._request_json(f"/api/ClosingPrice/GetClosingPriceInfo/{ins_code}")
        row = payload.get("closingPriceInfo") if isinstance(payload, dict) else None
        return row if isinstance(row, dict) and str(row.get("insCode")) == str(ins_code) else None

    async def fetch_order_book(self, ins_code: str) -> list[dict[str, Any]]:
        if not str(ins_code).isdigit():
            self.last_error = "Invalid InsCode."
            return []
        payload, _ = await self._request_json(f"/api/BestLimits/{ins_code}")
        rows = payload.get("bestLimits") if isinstance(payload, dict) else None
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []

    async def fetch_client_type(self, ins_code: str) -> dict[str, Any] | None:
        if not str(ins_code).isdigit():
            self.last_error = "Invalid InsCode."
            return None
        payload, _ = await self._request_json(f"/api/ClientType/GetClientType/{ins_code}/1/0")
        row = payload.get("clientType") if isinstance(payload, dict) else None
        return row if isinstance(row, dict) else None

    async def fetch_client_type_all(self) -> list[dict[str, Any]]:
        payload, _ = await self._request_json("/api/ClientType/GetClientTypeAll")
        rows = payload.get("clientTypeAllDto") if isinstance(payload, dict) else None
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []

    async def fetch_history(self, ins_code: str) -> list[dict[str, Any]]:
        if not str(ins_code).isdigit():
            self.last_error = "Invalid InsCode."
            return []
        payload, _ = await self._request_json(f"/api/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0")
        rows = payload.get("closingPriceDaily") if isinstance(payload, dict) else None
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []

    async def search_instruments(self, query: str) -> list[dict[str, Any]]:
        normalized = normalize_persian_text(query.strip())
        if not normalized or len(normalized) > 64:
            return []
        payload, _ = await self._request_json(
            f"/api/Instrument/GetInstrumentSearch/{quote(normalized, safe='')}"
        )
        rows = payload.get("instrumentSearch") if isinstance(payload, dict) else None
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
