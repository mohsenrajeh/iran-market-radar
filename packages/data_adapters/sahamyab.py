"""Sahamyab Data Adapter (Alternative source for VPN users)."""
import asyncio
import httpx
from typing import Any
from datetime import datetime

from packages.data_adapters.base import BaseDataAdapter
from packages.shared.logger import logger
from packages.shared.persian import normalize_persian_text, normalize_ticker

class SahamyabAdapter(BaseDataAdapter):
    """
    Sahamyab API Client.
    Useful for users who are using VPNs since TSETMC often blocks non-Iranian IPs.
    """

    def __init__(self):
        self.base_url = "https://www.sahamyab.com/guest/tw/twse"
        self.timeout = 15.0
        self.max_retries = 3
        self.semaphore = asyncio.Semaphore(5)

    async def _request(self, endpoint: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
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
                            f"Sahamyab HTTP {response.status_code} on {url}, attempt {attempt}/{self.max_retries}"
                        )
                except Exception as ex:
                    logger.warning(
                        f"Sahamyab request error on {url}: {ex}, attempt {attempt}/{self.max_retries}"
                    )
                
                await asyncio.sleep(2 * attempt)
        
        logger.error(f"Failed to fetch from Sahamyab after {self.max_retries} attempts: {url}")
        return None

    async def fetch_instrument_master(self) -> list[dict[str, Any]]:
        # Not fully supported via guest API easily, returning empty or fallback to TSETMC
        return []

    async def fetch_eod_history(self, symbol_or_code: str, days: int = 300) -> list[dict[str, Any]]:
        """Fetches closing price history for an instrument from Sahamyab."""
        data = await self._request("symbol/history", params={"v": "0.1", "code": symbol_or_code, "days": days})
        if not data or not data.get("success"):
            return []
        
        bars = []
        items = data.get("items", [])
        for item in items:
            date_str = item.get("date", "").split("T")[0]
            if not date_str:
                continue

            bars.append({
                "trading_date": date_str,
                "open": float(item.get("firstPrice", 0.0) or 0.0),
                "high": float(item.get("highPrice", 0.0) or 0.0),
                "low": float(item.get("lowPrice", 0.0) or 0.0),
                "close": float(item.get("closePrice", 0.0) or 0.0),
                "last": float(item.get("lastPrice", 0.0) or 0.0),
                "yesterday_price": float(item.get("yesterdayPrice", 0.0) or 0.0),
                "volume": int(item.get("tradeVolume", 0) or 0),
                "value": float(item.get("tradeValue", 0.0) or 0.0),
                "trade_count": int(item.get("tradeCount", 0) or 0),
            })
        
        # Sort bars ascending
        bars.sort(key=lambda x: x["trading_date"])
        return bars

    async def fetch_market_watch(self) -> list[dict[str, Any]]:
        return []

    async def fetch_client_type_history(self, symbol_or_code: str, days: int = 300) -> list[dict[str, Any]]:
        return []

    async def fetch_orderbook_depth(self, symbol_or_code: str) -> dict[str, Any] | None:
        return None
