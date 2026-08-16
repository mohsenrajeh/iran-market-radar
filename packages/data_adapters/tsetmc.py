"""TSETMC Official REST API Adapter."""
import asyncio
import httpx
from typing import Any
from packages.data_adapters.base import BaseDataAdapter
from packages.shared.config import settings
from packages.shared.logger import logger
from packages.shared.persian import normalize_persian_text, normalize_ticker


class TsetmcRestAdapter(BaseDataAdapter):
    """
    Official TSETMC REST API Client.
    Handles rate-limiting, exponential backoff, and response mapping to canonical entities.
    """

    def __init__(self):
        self.base_url = settings.tsetmc.base_url
        self.timeout = settings.tsetmc.request_timeout_seconds
        self.max_retries = settings.tsetmc.retry_attempts
        self.semaphore = asyncio.Semaphore(settings.tsetmc.max_concurrency)

    async def _request(self, endpoint: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "User-Agent": "IranMarketRadar/1.0 (Enterprise Compliance)",
            "Accept": "application/json",
        }
        
        async with self.semaphore:
            for attempt in range(1, self.max_retries + 1):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(url, params=params, headers=headers)
                        if response.status_code == 200:
                            return response.json()
                        logger.warning(
                            f"TSETMC HTTP {response.status_code} on {url}, attempt {attempt}/{self.max_retries}"
                        )
                except Exception as ex:
                    logger.warning(
                        f"TSETMC request error on {url}: {ex}, attempt {attempt}/{self.max_retries}"
                    )
                
                await asyncio.sleep(settings.tsetmc.backoff_initial_seconds * (2 ** (attempt - 1)))
        
        logger.error(f"Failed to fetch from TSETMC after {self.max_retries} attempts: {url}")
        return None

    async def fetch_instrument_master(self) -> list[dict[str, Any]]:
        """Fetches active market watch instruments."""
        data = await self._request("MarketData/GetMarketWatch")
        if not data or "marketwatch" not in data:
            return []
        
        instruments = []
        for item in data.get("marketwatch", []):
            instruments.append({
                "source_instrument_code": str(item.get("insCode", "")),
                "isin": str(item.get("lVal18AFC", "")),
                "ticker": normalize_persian_text(item.get("lVal30", "")),
                "ticker_normalized": normalize_ticker(item.get("lVal30", "")),
                "name_fa": normalize_persian_text(item.get("lVal18", "")),
                "market": "TSE" if item.get("flow") == 1 else "IFB",
                "board": str(item.get("board", "")),
                "base_volume": int(item.get("baseVol", 1)),
            })
        return instruments

    async def fetch_eod_history(self, symbol_or_code: str, days: int = 300) -> list[dict[str, Any]]:
        """Fetches closing price history for an instrument."""
        data = await self._request(f"ClosingPrice/GetClosingPriceDailyList/{symbol_or_code}/{days}")
        if not data or "closingPriceDaily" not in data:
            return []
        
        bars = []
        for item in data.get("closingPriceDaily", []):
            d_int = str(item.get("dEven", ""))
            if len(d_int) == 8:
                date_str = f"{d_int[:4]}-{d_int[4:6]}-{d_int[6:]}"
            else:
                date_str = "2026-01-01"

            bars.append({
                "trading_date": date_str,
                "open": float(item.get("priceFirst", 0.0)),
                "high": float(item.get("priceMax", 0.0)),
                "low": float(item.get("priceMin", 0.0)),
                "close": float(item.get("pClosing", 0.0)),
                "last": float(item.get("pDrCotVal", 0.0)),
                "yesterday_price": float(item.get("priceYesterday", 0.0)),
                "volume": int(item.get("qTotTran5J", 0)),
                "value": float(item.get("qTotCap", 0.0)),
                "trade_count": int(item.get("zTotTran", 0)),
            })
        return bars

    async def fetch_market_watch(self) -> list[dict[str, Any]]:
        """Fetches full market watch."""
        data = await self._request("MarketData/GetMarketWatch")
        if not data or "marketwatch" not in data:
            return []
        return data.get("marketwatch", [])

    async def fetch_client_type_history(self, symbol_or_code: str, days: int = 300) -> list[dict[str, Any]]:
        """Fetches حقیقی / حقوقی data."""
        data = await self._request(f"ClientType/GetClientTypeHistory/{symbol_or_code}/{days}")
        if not data or "clientType" not in data:
            return []
        return data.get("clientType", [])

    async def fetch_orderbook_depth(self, symbol_or_code: str) -> dict[str, Any] | None:
        """Fetches best 5 bid/ask levels."""
        data = await self._request(f"BestLimits/GetBestLimits/{symbol_or_code}")
        if not data or "bestLimits" not in data:
            return None
        return data


TSETMCAdapter = TsetmcRestAdapter
