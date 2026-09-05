"""Fail-closed BrsApi transport backup for TSETMC-derived reference data.

BrsApi documents full TSE/IFB snapshots plus price and client-type history.
The provider also states that these rows are collected from TSETMC, so this
adapter never creates an independent data vote and never marks rows tradeable.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
import jdatetime
import redis.asyncio as redis

from packages.shared.config import settings


class BrsApiAdapter:
    provider_name = "BrsApi"
    independence_key = "BRSAPI_TSETMC_DERIVED"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None, rate_store: Any | None = None):
        self.base_url = settings.brsapi.base_url.rstrip("/")
        self.api_key = settings.brsapi_api_key
        self.transport = transport
        self.rate_store = rate_store or (
            redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
            if transport is None else None
        )
        self.last_error: str | None = None
        self.last_response_at: datetime | None = None
        self._last_request_monotonic: float | None = None
        self._request_lock = asyncio.Lock()

    @property
    def configured(self) -> bool:
        return bool(settings.brsapi.enabled and self.api_key)

    def _safe_error(self, exc: Exception) -> str:
        # httpx exception strings may contain the fully rendered request URL.
        # Because this provider authenticates in the query string, even a raw
        # string replacement can miss a percent-encoded key. Persist only the
        # allowlisted exception class; detailed transport URLs stay out of logs,
        # receipts, and the public health endpoint.
        return type(exc).__name__[:128]

    async def _reserve_distributed_slot(self) -> bool:
        interval = max(0, int(settings.brsapi.minimum_request_interval_seconds))
        if interval == 0 or self.rate_store is None:
            return True
        try:
            reserved = await self.rate_store.set(
                "iran-market-radar:brsapi:request-window",
                "1",
                ex=max(1, interval),
                nx=True,
            )
            if reserved:
                return True
            ttl = await self.rate_store.ttl("iran-market-radar:brsapi:request-window")
            self.last_error = f"LOCAL_RATE_LIMIT: retry after {max(1, int(ttl))}s."
            return False
        except Exception as exc:
            self.last_error = f"RATE_LIMIT_STORE_UNAVAILABLE: {type(exc).__name__}"
            return False

    async def _get_list(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if not settings.brsapi.enabled:
            self.last_error = "BrsApi adapter is disabled."
            return []
        if not self.api_key:
            self.last_error = "BRSAPI_API_KEY is not configured."
            return []

        async with self._request_lock:
            interval = max(0, settings.brsapi.minimum_request_interval_seconds)
            now = time.monotonic()
            if self._last_request_monotonic is not None and now - self._last_request_monotonic < interval:
                remaining = int(interval - (now - self._last_request_monotonic)) + 1
                self.last_error = f"LOCAL_RATE_LIMIT: retry after {remaining}s."
                return []
            if not await self._reserve_distributed_slot():
                return []
            self._last_request_monotonic = now

            try:
                # BrsApi explicitly documents rejecting default Python/Go user
                # agents. Use a stable browser UA and still identify the system
                # through the Accept header and provider receipt.
                headers = {
                    "Accept": "application/json",
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/140.0 Safari/537.36"
                    ),
                }
                async with httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=settings.brsapi.request_timeout_seconds,
                    follow_redirects=False,
                    transport=self.transport,
                    proxy=settings.data_http_proxy if self.transport is None else None,
                    trust_env=settings.data_http_trust_env,
                    headers=headers,
                ) as client:
                    async with client.stream("GET", path, params={"key": self.api_key, **params}) as response:
                        if response.status_code != 200:
                            retry_after = response.headers.get("retry-after")
                            suffix = f"; retry-after={retry_after}" if retry_after else ""
                            self.last_error = f"BrsApi HTTP {response.status_code}{suffix}."
                            return []
                        if "json" not in response.headers.get("content-type", "").lower():
                            self.last_error = "BrsApi returned a non-JSON response."
                            return []
                        try:
                            header_date = parsedate_to_datetime(response.headers.get("date", ""))
                            self.last_response_at = header_date.astimezone(timezone.utc)
                        except (TypeError, ValueError, OverflowError):
                            self.last_response_at = None
                        content_length = response.headers.get("content-length")
                        if content_length and int(content_length) > settings.brsapi.max_response_bytes:
                            self.last_error = "BrsApi response exceeds the configured size limit."
                            return []
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > settings.brsapi.max_response_bytes:
                                self.last_error = "BrsApi response exceeded the configured size limit."
                                return []
                payload = json.loads(body)
                if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
                    self.last_error = "BrsApi response failed its documented list schema."
                    return []
                self.last_error = None
                return payload
            except Exception as exc:
                self.last_error = self._safe_error(exc)
                return []

    async def fetch_market_rows(self) -> list[dict[str, Any]]:
        """Return full-market rows for display/cross-check only."""
        rows = await self._get_list("/Tsetmc/AllSymbols.php", {"type": 1})
        required = {"time", "l18", "l30", "isin", "id", "py", "pl", "pc", "tvol"}
        accepted: list[dict[str, Any]] = []
        for row in rows:
            if not required.issubset(row):
                continue
            try:
                if not str(row["l18"]).strip() or not str(row["isin"]).strip():
                    continue
                if min(float(row["py"]), float(row["pl"]), float(row["pc"])) <= 0:
                    continue
                datetime.strptime(str(row["time"]), "%H:%M:%S")
            except (TypeError, ValueError):
                continue
            accepted.append(row)
        return accepted

    @staticmethod
    def _jalali_to_gregorian(raw_date: Any) -> str:
        parts = str(raw_date).replace("/", "-").split("-")
        if len(parts) != 3:
            raise ValueError("invalid Jalali date")
        year, month, day = (int(part) for part in parts)
        return jdatetime.date(year, month, day).togregorian().isoformat()

    async def fetch_eod_history(self, ticker: str) -> list[dict[str, Any]]:
        rows = await self._get_list("/Tsetmc/History.php", {"type": 0, "l18": ticker})
        normalized: list[dict[str, Any]] = []
        for row in rows:
            try:
                open_price = float(row["pf"])
                high = float(row["pmax"])
                low = float(row["pmin"])
                close = float(row["pc"])
                last = float(row["pl"])
                if min(open_price, high, low, close, last) <= 0 or high < low:
                    continue
                normalized.append({
                    "trading_date": self._jalali_to_gregorian(row["date"]),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "last": last,
                    "yesterday_price": float(row.get("py") or 0),
                    "volume": max(0, int(float(row.get("tvol") or 0))),
                    "value": max(0.0, float(row.get("tval") or 0)),
                    "trade_count": max(0, int(float(row.get("tno") or 0))),
                    "allowed_min": None,
                    "allowed_max": None,
                    "source": "BrsApi/TSETMC-derived",
                    "trade_eligible": False,
                })
            except (KeyError, TypeError, ValueError):
                continue
        return normalized

    async def fetch_client_type_history(self, ticker: str) -> list[dict[str, Any]]:
        rows = await self._get_list("/Tsetmc/History.php", {"type": 1, "l18": ticker})
        required = {
            "date", "Buy_CountI", "Buy_CountN", "Sell_CountI", "Sell_CountN",
            "Buy_I_Volume", "Buy_N_Volume", "Sell_I_Volume", "Sell_N_Volume",
        }
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not required.issubset(row):
                continue
            try:
                item = {"trading_date": self._jalali_to_gregorian(row["date"])}
                item.update({key: max(0, int(float(row[key]))) for key in required if key != "date"})
                item.update({"source": "BrsApi/TSETMC-derived", "trade_eligible": False})
            except (TypeError, ValueError):
                continue
            normalized.append(item)
        return normalized
