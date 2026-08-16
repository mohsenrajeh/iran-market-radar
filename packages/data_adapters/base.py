"""Abstract base data adapter protocol."""
from abc import ABC, abstractmethod
from typing import Any
from packages.domain.models import Instrument, EODBar, MarketSnapshot, OrderBookSnapshot, ClientTypeSnapshot, Filing


class BaseDataAdapter(ABC):
    """Abstract interface for all market data source adapters."""

    @abstractmethod
    async def fetch_instrument_master(self) -> list[dict[str, Any]]:
        """Fetches active and historical instruments from the source."""
        pass

    @abstractmethod
    async def fetch_eod_history(self, symbol_or_code: str, days: int = 300) -> list[dict[str, Any]]:
        """Fetches historical end-of-day daily bars."""
        pass

    @abstractmethod
    async def fetch_market_watch(self) -> list[dict[str, Any]]:
        """Fetches full market watch snapshot for all symbols."""
        pass

    @abstractmethod
    async def fetch_client_type_history(self, symbol_or_code: str, days: int = 300) -> list[dict[str, Any]]:
        """Fetches حقیقی / حقوقی flow history."""
        pass

    @abstractmethod
    async def fetch_orderbook_depth(self, symbol_or_code: str) -> dict[str, Any] | None:
        """Fetches current 5-level order book depth."""
        pass
