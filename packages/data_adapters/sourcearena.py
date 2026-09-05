"""Contract-checked SourceArena history adapter.

This adapter is deliberately not a live-trading replacement: the documented
history payload has no authoritative daily price-limit receipt. It can become
a historical backup after the owner configures a subscription token and the
runtime contract tests pass.
"""
from __future__ import annotations

import json
from typing import Any

import httpx
import jdatetime

from packages.shared.config import settings


class SourceArenaAdapter:
    provider_name = "SourceArena"
    independence_key = "SOURCEARENA_TSETMC_DERIVED"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = settings.sourcearena.base_url.rstrip("/")
        self.token = settings.sourcearena_api_token
        self.transport = transport
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(settings.sourcearena.enabled and self.token)

    def _safe_error(self, exc: Exception) -> str:
        message = f"{type(exc).__name__}: {exc}"
        if self.token:
            message = message.replace(self.token, "[REDACTED]")
        return message[:512]

    async def _get_list(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        if not settings.sourcearena.enabled:
            self.last_error = "SourceArena adapter is disabled."
            return []
        if not self.token:
            self.last_error = "SOURCEARENA_API_TOKEN is not configured."
            return []
        safe_params = {"token": self.token, **params}
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=settings.sourcearena.request_timeout_seconds,
                follow_redirects=False,
                transport=self.transport,
                proxy=settings.data_http_proxy if self.transport is None else None,
                trust_env=settings.data_http_trust_env,
                headers={"Accept": "application/json", "User-Agent": "IranMarketRadar/2.0 paper-only"},
            ) as client:
                async with client.stream("GET", "/api/", params=safe_params) as response:
                    if response.status_code != 200:
                        self.last_error = f"SourceArena HTTP {response.status_code}."
                        return []
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > settings.sourcearena.max_response_bytes:
                            self.last_error = "SourceArena response exceeded the configured size limit."
                            return []
            payload = json.loads(body)
            if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
                self.last_error = "SourceArena response failed the documented list schema."
                return []
            self.last_error = None
            return payload
        except Exception as exc:
            self.last_error = self._safe_error(exc)
            return []

    async def fetch_market_rows(self) -> list[dict[str, Any]]:
        """Return documented TSE/IFB rows for contract checking, without trading approval."""
        rows = await self._get_list({"all": "", "type": 0})
        required = {"name", "instance_code", "close_price", "final_price", "highest_price", "lowest_price"}
        return [row for row in rows if required.issubset(row)]

    async def fetch_eod_history(self, ticker: str, *, days: int = 260) -> list[dict[str, Any]]:
        """Normalize documented Jalali daily candles; missing fields stay explicit zeros."""
        rows = await self._get_list({"name": ticker, "days": min(1000, max(1, days))})
        normalized: list[dict[str, Any]] = []
        for row in rows:
            try:
                year, month, day = (int(part) for part in str(row["date"]).split("/"))
                trading_date = jdatetime.date(year, month, day).togregorian().isoformat()
                open_price = float(row["first_price"])
                close_price = float(row["close_price"])
                high = float(row["highest_price"])
                low = float(row["lowest_price"])
                volume = int(float(row.get("trade_volume") or 0))
                if min(open_price, close_price, high, low) <= 0 or high < low:
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            normalized.append({
                "trading_date": trading_date,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close_price,
                "last": close_price,
                "yesterday_price": 0.0,
                "volume": max(0, volume),
                "value": 0.0,
                "trade_count": 0,
                "allowed_min": None,
                "allowed_max": None,
                "source": "SourceArena/TSETMC-derived",
                "trade_eligible": False,
            })
        return normalized
