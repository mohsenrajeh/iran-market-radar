"""Fail-closed history adapter for the official public TSETMC CDN.

The public CDN is an official TSETMC transport, but it has no published SLA in
this project.  Rows are therefore normalized for ingestion/cross-checking and
explicitly remain non-trade-eligible until the higher-level provenance gate
accepts the complete batch.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, TypedDict

import httpx

from packages.shared.config import settings
from packages.shared.persian import normalize_persian_text, normalize_ticker


class TsetmcCdnEodRow(TypedDict):
    source_instrument_code: str
    trading_date: str
    open: float
    high: float
    low: float
    close: float
    last: float
    yesterday_price: float
    volume: int
    value: float
    trade_count: int
    allowed_min: None
    allowed_max: None
    source: str
    trade_eligible: bool


class TsetmcCdnClientTypeRow(TypedDict):
    source_instrument_code: str
    trading_date: str
    real_buy_count: int
    real_buy_volume: int
    real_buy_value: float
    real_sell_count: int
    real_sell_volume: int
    real_sell_value: float
    legal_buy_count: int
    legal_buy_volume: int
    legal_buy_value: float
    legal_sell_count: int
    legal_sell_volume: int
    legal_sell_value: float
    source: str
    trade_eligible: bool


class TsetmcCdnHistoryAdapter:
    """Normalize official CDN price and client-type history without guessing."""

    provider_name = "TSETMC Public CDN"
    independence_key = "TSETMC"
    default_base_url = "https://cdn.tsetmc.com/api"
    browser_user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_response_bytes: int | None = None,
    ) -> None:
        self.transport = transport
        self.base_url = (base_url or self.default_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.tsetmc.request_timeout_seconds
        self.max_response_bytes = max_response_bytes or settings.tsetmc.max_response_bytes
        self.last_error: str | None = None

    @staticmethod
    def _validate_ins_code(ins_code: str | int) -> str:
        normalized = str(ins_code).strip()
        if not normalized.isdigit() or int(normalized) <= 0:
            raise ValueError("invalid instrument code")
        return normalized

    @staticmethod
    def _parse_date(value: Any, field: str) -> str:
        if isinstance(value, bool):
            raise ValueError(f"invalid {field}")
        raw = str(value).strip()
        if len(raw) != 8 or not raw.isdigit():
            raise ValueError(f"invalid {field}")
        return datetime.strptime(raw, "%Y%m%d").date().isoformat()

    @staticmethod
    def _number(row: dict[str, Any], key: str, *, positive: bool = False) -> float:
        raw = row.get(key)
        if raw is None or isinstance(raw, bool):
            raise ValueError(f"missing numeric field: {key}")
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError(f"non-finite field: {key}")
        if positive and value <= 0:
            raise ValueError(f"non-positive field: {key}")
        if not positive and value < 0:
            raise ValueError(f"negative field: {key}")
        return value

    @classmethod
    def _integer(cls, row: dict[str, Any], key: str) -> int:
        value = cls._number(row, key)
        if not value.is_integer():
            raise ValueError(f"non-integral field: {key}")
        return int(value)

    async def _get_rows(self, path: str, root_key: str) -> list[dict[str, Any]]:
        headers = {"Accept": "application/json", "User-Agent": self.browser_user_agent}
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                follow_redirects=False,
                transport=self.transport,
                proxy=(settings.data_http_proxy or None) if self.transport is None else None,
                trust_env=settings.data_http_trust_env,
                headers=headers,
            ) as client:
                async with client.stream("GET", path) as response:
                    if response.status_code != 200:
                        self.last_error = f"TSETMC CDN HTTP {response.status_code}."
                        return []
                    if "json" not in response.headers.get("content-type", "").lower():
                        self.last_error = "TSETMC CDN returned a non-JSON response."
                        return []
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_response_bytes:
                        self.last_error = "TSETMC CDN response exceeds the configured size limit."
                        return []
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_response_bytes:
                            self.last_error = "TSETMC CDN response exceeded the configured size limit."
                            return []

            payload = json.loads(body)
            if not isinstance(payload, dict) or set(payload) != {root_key}:
                self.last_error = "TSETMC CDN response failed its root contract."
                return []
            rows = payload[root_key]
            if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
                self.last_error = "TSETMC CDN history failed its list contract."
                return []
            return rows
        except (httpx.HTTPError, json.JSONDecodeError, UnicodeDecodeError, ValueError, OverflowError) as exc:
            self.last_error = type(exc).__name__
            return []

    async def fetch_instrument_identity(self, ins_code: str | int) -> dict[str, str] | None:
        """Resolve a numeric InsCode against TSETMC's own identity record."""
        self.last_error = None
        try:
            normalized_code = self._validate_ins_code(ins_code)
        except (TypeError, ValueError, OverflowError):
            self.last_error = "TSETMC CDN request parameters are invalid."
            return None
        headers = {"Accept": "application/json", "User-Agent": self.browser_user_agent}
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.timeout_seconds,
                follow_redirects=False, transport=self.transport,
                proxy=(settings.data_http_proxy or None) if self.transport is None else None,
                trust_env=settings.data_http_trust_env, headers=headers,
            ) as client:
                async with client.stream("GET", f"/Instrument/GetInstrumentInfo/{normalized_code}") as response:
                    if response.status_code != 200 or "json" not in response.headers.get("content-type", "").lower():
                        self.last_error = f"TSETMC CDN identity HTTP {response.status_code}."
                        return None
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_response_bytes:
                            self.last_error = "TSETMC CDN identity response exceeded the configured size limit."
                            return None
            payload = json.loads(body)
            if not isinstance(payload, dict) or set(payload) != {"instrumentInfo"}:
                raise ValueError("invalid identity root")
            info = payload["instrumentInfo"]
            if not isinstance(info, dict) or str(info.get("insCode") or "") != normalized_code:
                raise ValueError("identity code mismatch")
            isin = str(info.get("instrumentID") or "").strip().upper()
            ticker = normalize_persian_text(str(info.get("lVal18AFC") or "").strip())
            if len(isin) != 12 or not isin.startswith("IR") or not ticker:
                raise ValueError("invalid official identity")
            self.last_error = None
            return {
                "ins_code": normalized_code,
                "isin": isin,
                "ticker": ticker,
                "ticker_normalized": normalize_ticker(ticker),
                "name_fa": normalize_persian_text(str(info.get("lVal30") or "").strip()),
            }
        except (httpx.HTTPError, json.JSONDecodeError, UnicodeDecodeError, ValueError, OverflowError) as exc:
            self.last_error = type(exc).__name__
            return None

    @classmethod
    def _normalize_eod_row(cls, row: dict[str, Any], ins_code: str) -> TsetmcCdnEodRow | None:
        if str(row.get("insCode") or "").strip() != ins_code:
            raise ValueError("instrument identity mismatch")
        trading_date = cls._parse_date(row.get("dEven"), "dEven")
        volume = cls._integer(row, "qTotTran5J")
        value = cls._number(row, "qTotCap")
        trade_count = cls._integer(row, "zTotTran")
        open_price = cls._number(row, "priceFirst")
        high = cls._number(row, "priceMax")
        low = cls._number(row, "priceMin")
        close = cls._number(row, "pClosing", positive=True)
        last = cls._number(row, "pDrCotVal", positive=True)
        yesterday = cls._number(row, "priceYesterday", positive=True)

        # CDN explicitly includes exchange-calendar rows with no transactions.
        # They carry a valid reference close but cannot form an OHLCV candle.
        # The official feed can retain a stale firstPrice on a zero-transaction
        # calendar row. The three transaction counters are authoritative.
        if volume == value == trade_count == 0:
            return None
        if min(volume, value, trade_count, open_price, high, low) <= 0:
            raise ValueError("partially populated trading row")
        # The weighted closing price may legitimately sit outside the day's
        # executed min/max. First and last are actual transaction prices.
        if high < low or not all(low <= price <= high for price in (open_price, last)):
            raise ValueError("invalid session price range")
        return TsetmcCdnEodRow(
            source_instrument_code=ins_code,
            trading_date=trading_date,
            open=open_price,
            high=high,
            low=low,
            close=close,
            last=last,
            yesterday_price=yesterday,
            volume=volume,
            value=value,
            trade_count=trade_count,
            allowed_min=None,
            allowed_max=None,
            source="TSETMC_PUBLIC_CDN",
            trade_eligible=False,
        )

    @classmethod
    def _normalize_client_type_row(cls, row: dict[str, Any], ins_code: str) -> TsetmcCdnClientTypeRow:
        if str(row.get("insCode") or "").strip() != ins_code:
            raise ValueError("instrument identity mismatch")
        return TsetmcCdnClientTypeRow(
            source_instrument_code=ins_code,
            trading_date=cls._parse_date(row.get("recDate"), "recDate"),
            real_buy_count=cls._integer(row, "buy_I_Count"),
            real_buy_volume=cls._integer(row, "buy_I_Volume"),
            real_buy_value=cls._number(row, "buy_I_Value"),
            real_sell_count=cls._integer(row, "sell_I_Count"),
            real_sell_volume=cls._integer(row, "sell_I_Volume"),
            real_sell_value=cls._number(row, "sell_I_Value"),
            legal_buy_count=cls._integer(row, "buy_N_Count"),
            legal_buy_volume=cls._integer(row, "buy_N_Volume"),
            legal_buy_value=cls._number(row, "buy_N_Value"),
            legal_sell_count=cls._integer(row, "sell_N_Count"),
            legal_sell_volume=cls._integer(row, "sell_N_Volume"),
            legal_sell_value=cls._number(row, "sell_N_Value"),
            source="TSETMC_PUBLIC_CDN",
            trade_eligible=False,
        )

    async def fetch_eod_history(self, ins_code: str | int, days: int = 300) -> list[TsetmcCdnEodRow]:
        """Return the newest ``days`` contract-valid EOD rows."""
        self.last_error = None
        try:
            normalized_code = self._validate_ins_code(ins_code)
            if isinstance(days, bool) or int(days) <= 0:
                raise ValueError("invalid days")
        except (TypeError, ValueError, OverflowError):
            self.last_error = "TSETMC CDN request parameters are invalid."
            return []
        rows = await self._get_rows(
            f"/ClosingPrice/GetClosingPriceDailyList/{normalized_code}/0",
            "closingPriceDaily",
        )
        if not rows:
            return []
        try:
            normalized: list[TsetmcCdnEodRow] = []
            for row in rows:
                item = self._normalize_eod_row(row, normalized_code)
                if item is not None:
                    normalized.append(item)
                if len(normalized) >= int(days):
                    break
        except (TypeError, ValueError, OverflowError):
            self.last_error = "TSETMC CDN EOD history failed row validation."
            return []
        self.last_error = None
        return normalized[: int(days)]

    async def fetch_client_type_history(
        self, ins_code: str | int, days: int = 300
    ) -> list[TsetmcCdnClientTypeRow]:
        """Return the newest ``days`` contract-valid حقیقی/حقوقی rows."""
        self.last_error = None
        try:
            normalized_code = self._validate_ins_code(ins_code)
            if isinstance(days, bool) or int(days) <= 0:
                raise ValueError("invalid days")
        except (TypeError, ValueError, OverflowError):
            self.last_error = "TSETMC CDN request parameters are invalid."
            return []
        rows = await self._get_rows(
            f"/ClientType/GetClientTypeHistory/{normalized_code}",
            "clientType",
        )
        if not rows:
            return []
        try:
            normalized = [
                self._normalize_client_type_row(row, normalized_code)
                for row in rows[: int(days)]
            ]
        except (TypeError, ValueError, OverflowError):
            self.last_error = "TSETMC CDN client-type history failed row validation."
            return []
        self.last_error = None
        return normalized[: int(days)]


TSETMCCdnHistoryAdapter = TsetmcCdnHistoryAdapter
