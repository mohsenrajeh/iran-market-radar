"""Structured JSON logging for Iran Market Radar."""
import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "component"):
            log_obj["component"] = record.component
        if hasattr(record, "symbol"):
            log_obj["symbol"] = record.symbol
        if hasattr(record, "event_id"):
            log_obj["event_id"] = record.event_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logger(name: str = "iran_market_radar", level: str = "INFO") -> logging.Logger:
    """Configures structured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        # Ensure utf-8 stream output on Windows terminals
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


logger = setup_logger()
