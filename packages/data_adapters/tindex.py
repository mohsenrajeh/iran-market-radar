"""Documented Tindex secondary adapter.

Tindex is intentionally a cross-check/fallback source. Its public contract caps
the free plan at one request per minute and does not publish its CODAL-derived
fundamental/valuation datasets, so it must never silently replace either the
official full-market feed or an independent fundamental source.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
import redis.asyncio as redis

from packages.shared.config import settings


class TindexAdapter:
    provider_name = "Tindex"
    independence_key = "TINDEX_TSETMC_DERIVED"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None, rate_store: Any | None = None):
        self.base_url = settings.tindex.base_url.rstrip("/")
        self.token = settings.tindex_api_token
        self.timeout = settings.tindex.request_timeout_seconds
        self.max_response_bytes = settings.tindex.max_response_bytes
        self.minimum_interval = settings.tindex.minimum_request_interval_seconds
        self.daily_success_limit = settings.tindex.daily_success_limit
        self.transport = transport
        self.rate_store = rate_store or (
            redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
            if transport is None else None
        )
        self.last_error: str | None = None
        self._last_request_monotonic: float | None = None
        self._request_lock = asyncio.Lock()

    async def _reserve_distributed_slot(self) -> bool:
        """Reserve minute and conservative daily allowances before network I/O.

        The daily counter intentionally counts attempts, not only successes. That
        under-utilizes the free plan during provider failures but guarantees this
        client never exceeds the documented 100-success ceiling after a partial
        Redis outage.
        """
        if self.minimum_interval <= 0 or self.rate_store is None:
            return True
        tehran_day = datetime.now(ZoneInfo("Asia/Tehran")).date().isoformat()
        daily_key = f"iran-market-radar:tindex:success:{tehran_day}"
        minute_key = "iran-market-radar:tindex:request-window"
        try:
            reserved = await self.rate_store.set(
                minute_key,
                "1",
                ex=max(1, int(self.minimum_interval)),
                nx=True,
            )
            if not reserved:
                ttl = await self.rate_store.ttl(minute_key)
                self.last_error = f"LOCAL_RATE_LIMIT: retry after {max(1, int(ttl))}s."
                return False
            daily_count = int(await self.rate_store.incr(daily_key))
            if daily_count == 1:
                await self.rate_store.expire(daily_key, 172800)
            if daily_count > self.daily_success_limit:
                await self.rate_store.decr(daily_key)
                await self.rate_store.delete(minute_key)
                self.last_error = "LOCAL_DAILY_LIMIT: Tindex conservative daily allowance is exhausted."
                return False
            return True
        except Exception as exc:
            self.last_error = f"RATE_LIMIT_STORE_UNAVAILABLE: {type(exc).__name__}"
            return False

    async def _record_success(self) -> None:
        # The conservative allowance is reserved before network access.
        return

    @property
    def configured(self) -> bool:
        return bool(settings.tindex.enabled and self.token)

    async def _get_envelope(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if not settings.tindex.enabled:
            self.last_error = "Tindex adapter is disabled."
            return None
        if not self.token:
            self.last_error = "TINDEX_API_TOKEN is not configured."
            return None

        async with self._request_lock:
            now = time.monotonic()
            if self._last_request_monotonic is not None:
                elapsed = now - self._last_request_monotonic
                if elapsed < self.minimum_interval:
                    self.last_error = (
                        "LOCAL_RATE_LIMIT: Tindex minimum request interval has not elapsed; "
                        f"retry after {int(self.minimum_interval - elapsed) + 1}s."
                    )
                    return None
            self._last_request_monotonic = now
            if not await self._reserve_distributed_slot():
                return None

            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    follow_redirects=False,
                    transport=self.transport,
                    proxy=settings.data_http_proxy if self.transport is None else None,
                    trust_env=settings.data_http_trust_env,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/json",
                        "User-Agent": "IranMarketRadar/2.0 paper-only",
                    },
                ) as client:
                    async with client.stream("GET", path, params=params) as response:
                        if response.status_code != 200:
                            retry_after = response.headers.get("retry-after")
                            suffix = f"; retry-after={retry_after}" if retry_after else ""
                            self.last_error = f"Tindex HTTP {response.status_code}{suffix}."
                            return None
                        content_length = response.headers.get("content-length")
                        if content_length and int(content_length) > self.max_response_bytes:
                            self.last_error = "Tindex response exceeds configured size limit."
                            return None
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > self.max_response_bytes:
                                self.last_error = "Tindex response exceeded size limit while streaming."
                                return None
                        if "json" not in response.headers.get("content-type", "").lower():
                            self.last_error = "Tindex returned a non-JSON response."
                            return None
                await self._record_success()
                payload = json.loads(body)
                if not isinstance(payload, dict) or payload.get("success") is not True or "data" not in payload:
                    self.last_error = "Tindex response failed its documented envelope contract."
                    return None
                self.last_error = None
                return payload
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"[:512]
                return None

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        payload = await self._get_envelope(path, params=params)
        return payload.get("data") if payload else None

    async def fetch_market_overview(self) -> dict[str, Any] | None:
        data = await self._get("/api/public/stock-market/overview")
        return data if isinstance(data, dict) else None

    async def fetch_stock_page(self, page: int = 1, per_page: int = 100) -> list[dict[str, Any]]:
        envelope = await self.fetch_stock_page_envelope(page=page, per_page=per_page)
        return envelope["rows"] if envelope else []

    async def fetch_stock_page_envelope(self, page: int = 1, per_page: int = 100) -> dict[str, Any] | None:
        """Return one documented screener page plus pagination metadata.

        The caller owns paced page-walking. A page from this TSETMC-derived
        provider is reference-only and must never be promoted to an orderable
        instrument universe.
        """
        requested_page = max(1, page)
        requested_per_page = min(100, max(1, per_page))
        payload = await self._get_envelope(
            "/api/public/stocks/by-category/stock-energy",
            params={"page": requested_page, "per_page": requested_per_page, "sort": "ticker", "dir": "asc"},
        )
        if not payload:
            return None
        data = payload.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
            self.last_error = "Tindex stock screener response is missing documented rows."
            return None
        meta = payload.get("meta")
        if not isinstance(meta, dict):
            self.last_error = "Tindex stock screener response is missing documented pagination metadata."
            return None
        rows = [row for row in data["rows"] if isinstance(row, dict)]
        try:
            page_value = max(1, int(meta.get("page", requested_page)))
            total = max(0, int(meta.get("total", len(rows))))
            last_page = max(1, int(meta.get("last_page", 1)))
        except (TypeError, ValueError):
            self.last_error = "Tindex stock screener pagination metadata is invalid."
            return None
        self.last_error = None
        return {
            "rows": rows,
            "meta": {
                "page": page_value,
                "per_page": min(100, max(1, int(meta.get("per_page", requested_per_page)))),
                "total": total,
                "has_more": bool(meta.get("has_more", page_value < last_page)),
                "last_page": last_page,
            },
        }

    async def fetch_symbol_overview(self, ticker_or_slug: str) -> dict[str, Any] | None:
        data = await self._get(f"/api/public/stock-market/symbol/{quote(ticker_or_slug, safe='')}/overview")
        return data if isinstance(data, dict) else None

    async def fetch_symbol_flow(self, ticker_or_slug: str) -> dict[str, Any] | None:
        data = await self._get(f"/api/public/stock-market/symbol/{quote(ticker_or_slug, safe='')}/flow")
        return data if isinstance(data, dict) else None

    async def fetch_symbol_candles(self, ticker_or_slug: str) -> list[dict[str, Any]]:
        data = await self._get(
            f"/api/public/stock-market/symbol/{quote(ticker_or_slug, safe='')}/candles",
            params={"range": "3m", "interval": "daily"},
        )
        if not isinstance(data, dict):
            return []
        columns = [data.get(key) for key in ("t", "o", "h", "l", "c")]
        if not all(isinstance(column, list) for column in columns):
            self.last_error = "Tindex candle response is missing documented columns."
            return []
        if len({len(column) for column in columns}) != 1:
            self.last_error = "Tindex candle columns have inconsistent lengths."
            return []
        decoded_days: list[int] = []
        for index, raw_value in enumerate(columns[0]):
            value = int(raw_value)
            decoded_days.append(value if index == 0 else decoded_days[-1] + value)
        epoch = date(1970, 1, 1)
        candles = []
        for index, epoch_days in enumerate(decoded_days):
            candle = {
                "trading_date": (epoch + timedelta(days=epoch_days)).isoformat(),
                "open": float(columns[1][index]),
                "high": float(columns[2][index]),
                "low": float(columns[3][index]),
                "close": float(columns[4][index]),
                "partial": bool((data.get("partial") or [False] * len(decoded_days))[index]),
                "source": "Tindex/TSETMC-derived",
            }
            if min(candle["open"], candle["high"], candle["low"], candle["close"]) > 0:
                candles.append(candle)
        return candles
