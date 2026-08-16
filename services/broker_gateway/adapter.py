"""Broker Gateway interface (Fail-Closed Phase 1 Safety Barrier)."""
from abc import ABC, abstractmethod
from typing import Any
from packages.shared.config import settings
from packages.shared.logger import logger


class BrokerAdapter(ABC):
    """Abstract interface for authorized broker integrations."""

    @abstractmethod
    async def connect(self, credentials: dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def send_order(self, order_intent: dict[str, Any]) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_portfolio_balances(self) -> dict[str, Any]:
        pass


class LiveBrokerGateway:
    """
    Phase 1 Safety Gate:
    Strictly fail-closed unless TRADING_MODE=live, LIVE_TRADING_ENABLED=true,
    and an authorized BrokerAdapter is explicitly configured.
    """

    def __init__(self, adapter: BrokerAdapter | None = None):
        self.adapter = adapter

    def is_live_execution_allowed(self) -> bool:
        return (
            settings.trading_mode == "live"
            and settings.live_trading_enabled is True
            and self.adapter is not None
        )

    async def execute_live_order(self, order_intent: dict[str, Any]) -> dict[str, Any]:
        if not self.is_live_execution_allowed():
            logger.critical("LIVE ORDER BLOCKED: System is in Paper/Analytical mode.")
            raise PermissionError("معاملات مستقیم کارگزاری در فاز یک غیرفعال است (Fail-Closed).")

        return await self.adapter.send_order(order_intent)
