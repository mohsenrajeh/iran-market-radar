"""Fail-closed adapter for CODAL's official public disclosure search API.

The search endpoint is useful as an independent source of *disclosures*.  It
does not expose audited financial metrics in the search result itself, so this
adapter intentionally returns only document identity and publication metadata.
"""
from __future__ import annotations

import json
import re
from typing import Any, TypedDict
from urllib.parse import urljoin, urlparse

import httpx

from packages.shared.config import settings
from packages.shared.persian import normalize_persian_text, normalize_ticker, to_ascii_digits


class CodalDisclosure(TypedDict):
    tracing_no: int
    symbol: str
    symbol_normalized: str
    company_name: str
    title: str
    publish_date_time: str | None
    sent_date_time: str | None
    url: str | None
    letter_code: str | None
    source: str


class CodalPublicAdapter:
    """Bounded transport and schema validation for official CODAL search."""

    provider_name = "CODAL public search"
    independence_key = "CODAL_OFFICIAL_PUBLIC"
    default_base_url = "https://search.codal.ir"
    search_path = "/api/search/v2/q"
    browser_user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
    _date_time_pattern = re.compile(r"^\d{4}/\d{2}/\d{2}(?: \d{2}:\d{2}:\d{2})?$")
    _allowed_url_hosts = frozenset({"codal.ir", "www.codal.ir", "search.codal.ir"})

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 15.0,
        max_response_bytes: int | None = None,
    ) -> None:
        self.transport = transport
        self.base_url = (base_url or self.default_base_url).rstrip("/")
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 60.0))
        self.max_response_bytes = max_response_bytes or settings.tsetmc.max_response_bytes
        self.last_error: str | None = None
        self.last_total: int | None = None
        self.last_page_count: int | None = None

    @staticmethod
    def _clean_required_text(value: Any, field: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"invalid {field}")
        normalized = normalize_persian_text(value)
        if not normalized:
            raise ValueError(f"empty {field}")
        return normalized

    @classmethod
    def _clean_optional_text(cls, value: Any, field: str) -> str | None:
        if value in (None, ""):
            return None
        return cls._clean_required_text(value, field)

    @classmethod
    def _clean_date_time(cls, value: Any, field: str) -> str | None:
        cleaned = cls._clean_optional_text(value, field)
        if cleaned is None:
            return None
        cleaned = to_ascii_digits(cleaned)
        if not cls._date_time_pattern.fullmatch(cleaned):
            raise ValueError(f"invalid {field}")
        return cleaned

    @classmethod
    def _clean_url(cls, value: Any) -> str | None:
        if value in (None, ""):
            return None
        if not isinstance(value, str):
            raise ValueError("invalid Url")
        absolute = urljoin("https://codal.ir/", value.strip())
        parsed = urlparse(absolute)
        if parsed.scheme != "https" or parsed.hostname not in cls._allowed_url_hosts:
            raise ValueError("untrusted Url")
        return absolute

    @classmethod
    def _normalize_letter(cls, row: dict[str, Any]) -> CodalDisclosure:
        tracing_raw = row.get("TracingNo")
        if isinstance(tracing_raw, bool):
            raise ValueError("invalid TracingNo")
        tracing_no = int(tracing_raw)
        if tracing_no <= 0:
            raise ValueError("invalid TracingNo")

        symbol = cls._clean_required_text(row.get("Symbol"), "Symbol")
        return CodalDisclosure(
            tracing_no=tracing_no,
            symbol=symbol,
            symbol_normalized=normalize_ticker(symbol),
            company_name=cls._clean_required_text(row.get("CompanyName"), "CompanyName"),
            title=cls._clean_required_text(row.get("Title"), "Title"),
            publish_date_time=cls._clean_date_time(row.get("PublishDateTime"), "PublishDateTime"),
            sent_date_time=cls._clean_date_time(row.get("SentDateTime"), "SentDateTime"),
            url=cls._clean_url(row.get("Url")),
            letter_code=(
                to_ascii_digits(cleaned_letter_code)
                if (cleaned_letter_code := cls._clean_optional_text(row.get("LetterCode"), "LetterCode"))
                else None
            ),
            source="CODAL official public search",
        )

    async def fetch_disclosures(
        self,
        *,
        page_number: int = 1,
        page_size: int = 20,
        symbol: str | None = None,
    ) -> list[CodalDisclosure]:
        """Fetch one bounded search page; any contract violation rejects it."""
        if isinstance(page_number, bool) or not 1 <= page_number <= 1_000_000:
            self.last_error = "CODAL page number is outside the allowed range."
            return []
        if isinstance(page_size, bool) or not 1 <= page_size <= 100:
            self.last_error = "CODAL page size is outside the allowed range."
            return []

        params: dict[str, Any] = {"PageNumber": page_number, "PageSize": page_size}
        if symbol is not None:
            normalized_symbol = normalize_ticker(symbol)
            if not normalized_symbol or len(normalized_symbol) > 32:
                self.last_error = "CODAL symbol is invalid."
                return []
            params["Symbol"] = normalized_symbol

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
                async with client.stream("GET", self.search_path, params=params) as response:
                    if response.status_code != 200:
                        self.last_error = f"CODAL HTTP {response.status_code}."
                        return []
                    if "json" not in response.headers.get("content-type", "").lower():
                        self.last_error = "CODAL returned a non-JSON response."
                        return []
                    length = response.headers.get("content-length")
                    try:
                        if length is not None and int(length) > self.max_response_bytes:
                            self.last_error = "CODAL response exceeds the configured size limit."
                            return []
                    except ValueError:
                        self.last_error = "CODAL returned an invalid content length."
                        return []

                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_response_bytes:
                            self.last_error = "CODAL response exceeded the configured size limit."
                            return []

            payload = json.loads(body)
            if not isinstance(payload, dict) or set(("Total", "Page", "Letters")) - payload.keys():
                raise ValueError("invalid root schema")
            total, page_count, letters = payload["Total"], payload["Page"], payload["Letters"]
            if (
                isinstance(total, bool)
                or isinstance(page_count, bool)
                or not isinstance(total, int)
                or not isinstance(page_count, int)
                or total < 0
                or page_count < 0
                or not isinstance(letters, list)
                # The public endpoint currently returns its fixed server-side
                # page size (20) even when a smaller PageSize is requested.
                # Keep a hard client bound without mistaking that behaviour
                # for a schema failure.
                or len(letters) > 100
                or not all(isinstance(row, dict) for row in letters)
            ):
                raise ValueError("invalid root values")

            normalized = [self._normalize_letter(row) for row in letters]
            self.last_total = total
            self.last_page_count = page_count
            self.last_error = None
            return normalized
        except (json.JSONDecodeError, TypeError, ValueError):
            self.last_error = "CODAL response failed its documented schema."
            self.last_total = None
            self.last_page_count = None
            return []
        except Exception as exc:
            # Error strings can include rendered URLs. Retain only the type.
            self.last_error = type(exc).__name__[:128]
            self.last_total = None
            self.last_page_count = None
            return []
