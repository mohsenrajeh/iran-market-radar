"""Validated transport adapter for the official TSE WebGW market watch.

The bulk WebGW response does not carry a trustworthy observation timestamp.
Callers must therefore provide an aware batch clock obtained from a separately
validated official source.  The adapter never substitutes the local wall clock.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, TypedDict

import httpx

from packages.shared.config import settings
from packages.shared.persian import normalize_persian_text, normalize_ticker


class TseWebGwMarketRow(TypedDict):
    """Canonical, provenance-ready representation of a WebGW market row."""

    source_instrument_code: str
    isin: str
    ticker: str
    ticker_normalized: str
    name_fa: str
    open: float | None
    high: float | None
    low: float | None
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
    market: str
    observed_at: str
    source: str


class TseWebGwAdapter:
    """Official public WebGW adapter with a strict, fail-closed contract."""

    provider_name = "TSE WebGW"
    independence_key = "TSE_OFFICIAL_WEBGW"
    default_base_url = "https://webgw.tse.ir/InstrumentProvider/api/v1"
    market_watch_path = "/MarketWatch/MarketWatchCash/fa"
    browser_user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
    _isin_pattern = re.compile(r"^IR[A-Z0-9]{10}$")

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 15.0,
        max_response_bytes: int | None = None,
        max_response_age_seconds: int | None = None,
        max_future_skew_seconds: int = 30,
    ) -> None:
        self.transport = transport
        self.base_url = (base_url or self.default_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes or settings.tsetmc.max_response_bytes
        self.max_response_age_seconds = (
            max_response_age_seconds
            if max_response_age_seconds is not None
            else max(60, settings.quality.critical_market_stale_seconds)
        )
        self.max_future_skew_seconds = max_future_skew_seconds
        self.last_error: str | None = None
        self.last_response_at: datetime | None = None
        self.rejected_row_count = 0

    @staticmethod
    def _metric_value(row: dict[str, Any], key: str) -> Any:
        metric = row.get(key)
        if not isinstance(metric, dict) or "value" not in metric:
            raise ValueError(f"missing metric: {key}")
        return metric["value"]

    @classmethod
    def _required_number(cls, row: dict[str, Any], key: str, *, positive: bool = False) -> float:
        raw = cls._metric_value(row, key)
        if isinstance(raw, bool):
            raise ValueError(f"invalid numeric metric: {key}")
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError(f"non-finite metric: {key}")
        if positive and value <= 0:
            raise ValueError(f"non-positive metric: {key}")
        if not positive and value < 0:
            raise ValueError(f"negative metric: {key}")
        return value

    @classmethod
    def _optional_positive_metric(cls, row: dict[str, Any], key: str) -> float | None:
        try:
            value = cls._required_number(row, key)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    @classmethod
    def _optional_metric(cls, row: dict[str, Any], key: str) -> float | None:
        try:
            raw = cls._metric_value(row, key)
            if isinstance(raw, bool):
                return None
            value = float(raw)
            return value if math.isfinite(value) else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _plain_number(row: dict[str, Any], key: str, *, positive: bool = False) -> float:
        raw = row.get(key)
        if isinstance(raw, bool) or raw is None:
            raise ValueError(f"missing numeric field: {key}")
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError(f"non-finite field: {key}")
        if positive and value <= 0:
            raise ValueError(f"non-positive field: {key}")
        if not positive and value < 0:
            raise ValueError(f"negative field: {key}")
        return value

    @staticmethod
    def _nonnegative_int(value: float, key: str) -> int:
        if not value.is_integer():
            raise ValueError(f"non-integral count: {key}")
        return int(value)

    @classmethod
    def _normalize_row(cls, row: dict[str, Any], observed_at: datetime) -> TseWebGwMarketRow:
        isin = str(row.get("instrumentId") or "").strip().upper()
        ticker = normalize_persian_text(str(row.get("instrumentName") or "").strip())
        name = normalize_persian_text(str(row.get("companyNamePersian") or "").strip())
        if not cls._isin_pattern.fullmatch(isin):
            raise ValueError("invalid ISIN")
        if not ticker or not name:
            raise ValueError("missing instrument identity")

        last = cls._required_number(row, "lastPrice", positive=True)
        close = cls._required_number(row, "closingPrice", positive=True)
        yesterday = cls._required_number(row, "yesterdayPrice", positive=True)
        volume = cls._nonnegative_int(cls._required_number(row, "tradeVolume"), "tradeVolume")
        value = cls._required_number(row, "tradeValue")
        trade_count = cls._nonnegative_int(cls._required_number(row, "tradeCount"), "tradeCount")
        allowed_min = cls._plain_number(row, "minValue", positive=True)
        allowed_max = cls._plain_number(row, "maxValue", positive=True)
        if allowed_max < allowed_min:
            raise ValueError("invalid allowed price range")

        high = cls._optional_positive_metric(row, "highValue")
        low = cls._optional_positive_metric(row, "lowValue")
        if high is not None and low is not None and high < low:
            raise ValueError("invalid session price range")

        return TseWebGwMarketRow(
            source_instrument_code=isin,
            isin=isin,
            ticker=ticker,
            ticker_normalized=normalize_ticker(ticker),
            name_fa=name,
            open=cls._optional_positive_metric(row, "firstPrice"),
            high=high,
            low=low,
            last=last,
            close=close,
            yesterday_price=yesterday,
            volume=volume,
            value=value,
            trade_count=trade_count,
            allowed_min=allowed_min,
            allowed_max=allowed_max,
            pe=cls._optional_metric(row, "pe"),
            eps=cls._optional_metric(row, "eps"),
            market_value=cls._optional_positive_metric(row, "marketValue"),
            state=normalize_persian_text(str(row.get("statename") or "").strip()),
            market=normalize_persian_text(str(row.get("marketname") or "").strip()),
            observed_at=observed_at.isoformat(),
            source="TSE_WEBGW",
        )

    @staticmethod
    def _parse_http_date(raw_date: str | None) -> datetime:
        if not raw_date:
            raise ValueError("missing HTTP Date")
        parsed = parsedate_to_datetime(raw_date)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone-naive HTTP Date")
        return parsed.astimezone(timezone.utc)

    def _validate_response_clock(self, response_at: datetime) -> bool:
        now = datetime.now(timezone.utc)
        age_seconds = (now - response_at).total_seconds()
        if age_seconds > self.max_response_age_seconds:
            self.last_error = "TSE WebGW HTTP Date is stale."
            return False
        if age_seconds < -self.max_future_skew_seconds:
            self.last_error = "TSE WebGW HTTP Date is in the future."
            return False
        return True

    async def fetch_market_rows(self, *, batch_clock: datetime | None = None) -> list[TseWebGwMarketRow]:
        """Fetch rows using the response Date, or an explicit deterministic test clock."""
        self.rejected_row_count = 0
        self.last_response_at = None
        if batch_clock is not None and (batch_clock.tzinfo is None or batch_clock.utcoffset() is None):
            self.last_error = "WebGW batch clock is missing or timezone-naive."
            return []

        headers = {
            "Accept": "application/json",
            "User-Agent": self.browser_user_agent,
        }
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                follow_redirects=False,
                transport=self.transport,
                proxy=settings.data_http_proxy if self.transport is None else None,
                trust_env=settings.data_http_trust_env,
                headers=headers,
            ) as client:
                async with client.stream("GET", self.market_watch_path) as response:
                    if response.status_code != 200:
                        self.last_error = f"TSE WebGW HTTP {response.status_code}."
                        return []
                    if "json" not in response.headers.get("content-type", "").lower():
                        self.last_error = "TSE WebGW returned a non-JSON response."
                        return []
                    try:
                        response_at = batch_clock or self._parse_http_date(response.headers.get("date"))
                    except (TypeError, ValueError, OverflowError):
                        self.last_error = "TSE WebGW HTTP Date is missing or invalid."
                        return []
                    if batch_clock is None and not self._validate_response_clock(response_at):
                        return []
                    self.last_response_at = response_at
                    length = response.headers.get("content-length")
                    if length and int(length) > self.max_response_bytes:
                        self.last_error = "TSE WebGW response exceeds the configured size limit."
                        return []
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_response_bytes:
                            self.last_error = "TSE WebGW response exceeded the configured size limit."
                            return []

            payload = json.loads(body)
            if not isinstance(payload, dict) or "Items" not in payload:
                self.last_error = "TSE WebGW response failed its root contract."
                return []
            raw_rows = payload["Items"]
            if not isinstance(raw_rows, list) or not raw_rows or not all(isinstance(row, dict) for row in raw_rows):
                self.last_error = "TSE WebGW Items failed its list contract."
                return []

            accepted: list[TseWebGwMarketRow] = []
            for row in raw_rows:
                try:
                    accepted.append(self._normalize_row(row, response_at))
                except (TypeError, ValueError, OverflowError):
                    self.rejected_row_count += 1
            if not accepted:
                self.last_error = "TSE WebGW contained no contract-valid market rows."
                return []
            self.last_error = None
            return accepted
        except (httpx.HTTPError, json.JSONDecodeError, UnicodeDecodeError, ValueError, OverflowError) as exc:
            self.last_error = type(exc).__name__
            return []


TSEWebGWAdapter = TseWebGwAdapter
