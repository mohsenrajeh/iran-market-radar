"""Authenticated adapter for the documented api.tsetmc.com REST contract."""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from packages.data_adapters.base import BaseDataAdapter
from packages.shared.config import settings
from packages.shared.logger import logger
from packages.shared.persian import normalize_persian_text, normalize_ticker


class TsetmcRestAdapter(BaseDataAdapter):
    """Official TSETMC POST/JWT API with bounded responses and explicit schemas."""

    def __init__(self):
        self.base_url = settings.tsetmc.base_url.rstrip("/")
        self.timeout = settings.tsetmc.request_timeout_seconds
        self.max_retries = settings.tsetmc.retry_attempts
        self.semaphore = asyncio.Semaphore(settings.tsetmc.max_concurrency)
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self.last_error: str | None = None
        self.last_error_code: int | None = None

    @staticmethod
    def _notification(payload: dict[str, Any]) -> tuple[int | None, str | None]:
        raw = payload.get("Msg") or payload.get("msg") or payload.get("Message") or payload.get("message")
        if isinstance(raw, dict):
            code = raw.get("Code", raw.get("code"))
            message = raw.get("Msg", raw.get("msg"))
            try:
                normalized_code = int(code) if code is not None else None
            except (TypeError, ValueError):
                normalized_code = None
            return normalized_code, str(message)[:320] if message else None
        return None, str(raw)[:320] if raw else None

    @property
    def credentials_configured(self) -> bool:
        return bool(settings.tsetmc_api_username and settings.tsetmc_api_password)

    async def _read_json(self, response: httpx.Response) -> dict[str, Any]:
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > settings.tsetmc.max_response_bytes:
            raise ValueError("TSETMC response exceeds configured size limit")
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > settings.tsetmc.max_response_bytes:
                raise ValueError("TSETMC response exceeded configured size limit while streaming")
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type.lower():
            raise ValueError(f"Unexpected TSETMC content type: {content_type}")
        parsed = json.loads(body)
        if not isinstance(parsed, dict):
            raise ValueError("Unexpected TSETMC response schema: root is not an object")
        return parsed

    async def _login(self, client: httpx.AsyncClient) -> bool:
        if not self.credentials_configured:
            self.last_error = "TSETMC_API_USERNAME/TSETMC_API_PASSWORD are not configured."
            return False
        async with client.stream(
            "POST",
            f"{self.base_url}/Account/Login",
            json={"Username": settings.tsetmc_api_username, "Password": settings.tsetmc_api_password},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as response:
            if response.status_code != 200:
                self.last_error = f"TSETMC login returned HTTP {response.status_code}."
                return False
            payload = await self._read_json(response)
        data = payload.get("Data") or payload.get("data") or {}
        token = data.get("Token") or data.get("token")
        if not payload.get("IsSuccess", payload.get("isSuccess", False)) or not token:
            code, _message = self._notification(payload)
            self.last_error_code = code
            if code == -102:
                self.last_error = "اعتبارنامه TSETMC رد شد یا حساب API مسدود است (کد -102)."
            elif code == -107:
                self.last_error = "TSETMC تغییر رمز اولیه را الزامی کرده است (کد -107)."
            else:
                self.last_error = f"ورود TSETMC ناموفق بود (کد {code if code is not None else 'نامشخص'})."
            return False
        self._token = str(token)
        raw_expiry = data.get("ExpireDate") or data.get("expireDate")
        try:
            self._token_expires_at = datetime.fromisoformat(str(raw_expiry).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        self.last_error = None
        self.last_error_code = None
        return True

    async def _request(self, endpoint: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.credentials_configured:
            self.last_error = "Official TSETMC credentials are missing."
            return []
        limits = httpx.Limits(max_connections=settings.tsetmc.max_concurrency)
        async with self.semaphore, httpx.AsyncClient(
            timeout=self.timeout,
            limits=limits,
            follow_redirects=False,
            proxy=settings.data_http_proxy,
            trust_env=settings.data_http_trust_env,
        ) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    now = datetime.now(timezone.utc)
                    if not self._token or not self._token_expires_at or self._token_expires_at <= now + timedelta(seconds=30):
                        if not await self._login(client):
                            return []
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/{endpoint.lstrip('/')}",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {self._token}",
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                            "User-Agent": "IranMarketRadar/2.0 paper-only",
                        },
                    ) as response:
                        if response.status_code == 401:
                            self._token = None
                            self.last_error = "TSETMC token was rejected."
                        elif response.status_code == 200:
                            result = await self._read_json(response)
                            success = result.get("IsSuccess", result.get("isSuccess", False))
                            data = result.get("Data", result.get("data"))
                            if success and isinstance(data, list):
                                self.last_error = None
                                return [item for item in data if isinstance(item, dict)]
                            self.last_error = str(result.get("Message") or result.get("message") or "TSETMC schema/result failure")[:512]
                            return []
                        else:
                            self.last_error = f"TSETMC HTTP {response.status_code} on {endpoint}."
                except Exception as exc:
                    self.last_error = f"{type(exc).__name__}: {exc}"[:512]
                    logger.warning("TSETMC request attempt %s/%s failed for %s", attempt, self.max_retries, endpoint)
                if attempt < self.max_retries:
                    await asyncio.sleep(settings.tsetmc.backoff_initial_seconds * (2 ** (attempt - 1)))
        return []

    async def fetch_instrument_master(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for flow in (1, 2):
            rows.extend(await self._request("Instrument/Instrument", {"Flow": flow}))
        instruments: list[dict[str, Any]] = []
        for item in rows:
            code = item.get("InsCode")
            ticker = item.get("LVal18AFC") or item.get("LVal30")
            if not code or not ticker or int(item.get("Valid", 1) or 0) != 1:
                continue
            instruments.append({
                "source_instrument_code": str(code),
                "isin": str(item.get("InstrumentID") or item.get("CIsin") or ""),
                "ticker": normalize_persian_text(str(ticker)),
                "ticker_normalized": normalize_ticker(str(ticker)),
                "name_fa": normalize_persian_text(str(item.get("LSoc30") or item.get("LVal30") or ticker)),
                "market": "TSE" if int(item.get("Flow", flow)) == 1 else "IFB",
                "board": str(item.get("CComVal") or ""),
                "sector_code": str(item.get("CSecVal") or ""),
                "base_volume": int(item.get("BaseVol") or 1),
                "allowed_min": float(item.get("PSaiSMinOkValMdv") or 0),
                "allowed_max": float(item.get("PSaiSMaxOkValMdv") or 0),
            })
        return instruments

    async def fetch_market_watch(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for flow in (1, 2):
            rows.extend(await self._request("Trade/TradeLastDay", {"Flow": flow}))
        return rows

    async def fetch_eod_history(self, symbol_or_code: str, days: int = 300) -> list[dict[str, Any]]:
        end = date.today()
        start = end - timedelta(days=max(days * 2, days + 30))
        rows = await self._request("Trade/InstTrade", {
            "Inscode": int(symbol_or_code),
            "DateFrom": int(start.strftime("%Y%m%d")),
            "DateTo": int(end.strftime("%Y%m%d")),
        })
        bars: list[dict[str, Any]] = []
        for item in rows[-days:]:
            raw_date = str(item.get("DEven") or "")
            if len(raw_date) != 8 or not raw_date.isdigit():
                continue
            bars.append({
                "trading_date": f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}",
                "open": float(item.get("PriceFirst") or 0),
                "high": float(item.get("PriceMax") or 0),
                "low": float(item.get("PriceMin") or 0),
                "close": float(item.get("PClosing") or 0),
                "last": float(item.get("PDrCotVal") or 0),
                "yesterday_price": float(item.get("PriceYesterday") or 0),
                "volume": int(item.get("QTotTran5J") or 0),
                "value": float(item.get("QTotCap") or 0),
                "trade_count": int(item.get("ZTotTran") or 0),
            })
        return [bar for bar in bars if min(bar["open"], bar["high"], bar["low"], bar["close"], bar["yesterday_price"]) > 0]

    async def fetch_client_type_history(self, symbol_or_code: str, days: int = 300) -> list[dict[str, Any]]:
        rows = await self._request("ClientType/ClientTypeByInsCode", {"Inscode": int(symbol_or_code)})
        normalized: list[dict[str, Any]] = []
        for item in rows[-days:]:
            raw_date = str(item.get("RecDate") or "")
            if len(raw_date) != 8 or not raw_date.isdigit():
                continue
            normalized.append({
                "trading_date": f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}",
                "real_buy_count": int(item.get("Buy_Count_ClientI") or 0),
                "real_buy_volume": int(item.get("Buy_I_Volume") or 0),
                "real_buy_value": float(item.get("Buy_I_Value") or 0),
                "real_sell_count": int(item.get("Sell_Count_ClientI") or 0),
                "real_sell_volume": int(item.get("Sell_I_Volume") or 0),
                "real_sell_value": float(item.get("Sell_I_Value") or 0),
                "legal_buy_count": int(item.get("Buy_Count_ClientN") or 0),
                "legal_buy_volume": int(item.get("Buy_N_Volume") or 0),
                "legal_buy_value": float(item.get("Buy_N_Value") or 0),
                "legal_sell_count": int(item.get("Sell_Count_ClientN") or 0),
                "legal_sell_volume": int(item.get("Sell_N_Volume") or 0),
                "legal_sell_value": float(item.get("Sell_N_Value") or 0),
            })
        return normalized

    async def fetch_indices(self, flow: int = 1) -> list[dict[str, Any]]:
        return await self._request("Index/IndexB1LastDayLastData", {"Flow": flow})

    async def fetch_thresholds(self) -> dict[str, tuple[float, float]]:
        rows: list[dict[str, Any]] = []
        for flow in (1, 2):
            rows.extend(await self._request("MarketInfo/Threshold", {"Flow": flow}))
        return {
            str(item["InsCode"]): (float(item["PSGelStaMin"]), float(item["PSGelStaMax"]))
            for item in rows
            if item.get("InsCode") and float(item.get("PSGelStaMin") or 0) > 0 and float(item.get("PSGelStaMax") or 0) > 0
        }

    async def fetch_orderbook_depth(self, symbol_or_code: str) -> dict[str, Any] | None:
        # The documented BestLimit contract is intentionally not guessed here.
        return None


TSETMCAdapter = TsetmcRestAdapter
