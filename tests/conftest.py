"""Hard isolation boundary for the test suite.

This file is loaded by pytest before test modules import the application.  It
must override the developer/Compose environment so tests can never migrate or
write the live paper-trading database.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


_test_root = Path(tempfile.mkdtemp(prefix="iran_market_radar_pytest_"))
_test_db = (_test_root / "suite.sqlite3").as_posix()

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db}"
os.environ["DATABASE_SYNC_URL"] = f"sqlite:///{_test_db}"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/15"
os.environ["SESSION_SECRET"] = "pytest-isolated-session-secret-not-for-runtime"
os.environ["RADAR_ADMIN_USER"] = "pytest-admin"
os.environ["RADAR_ADMIN_PASSWORD"] = "pytest-password"
os.environ["TSETMC_API_USERNAME"] = ""
os.environ["TSETMC_API_PASSWORD"] = ""
os.environ["TINDEX_API_TOKEN"] = ""
os.environ["BRSAPI_API_KEY"] = ""
os.environ["SOURCEARENA_API_TOKEN"] = ""
os.environ["API_IR_TOKEN"] = ""
os.environ["AUTO_PAPER_TRADING_ENABLED"] = "false"
os.environ["LIVE_TRADING_ENABLED"] = "false"
os.environ["TRADING_MODE"] = "paper"
