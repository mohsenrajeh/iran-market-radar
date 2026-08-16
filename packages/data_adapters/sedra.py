"""Codal / SEDRA Official REST API Adapter."""
from typing import Any
from packages.shared.config import settings
from packages.shared.logger import logger


class SedraAdapter:
    """
    Adapter for SEDRA / Codal financial disclosures.
    Point-in-time rule: filings become available at published_at timestamp, never period_end date.
    """

    def __init__(self):
        self.enabled = settings.sedra.enabled
        self.base_url = settings.sedra.base_url

    async def fetch_recent_filings(self, days: int = 30) -> list[dict[str, Any]]:
        """Fetches corporate filings."""
        if not self.enabled:
            logger.info("SEDRA adapter disabled (waiting for enterprise credentials). Returning empty.")
            return []
        # When live credentials are provided, connects to SEDRA REST web service.
        return []
