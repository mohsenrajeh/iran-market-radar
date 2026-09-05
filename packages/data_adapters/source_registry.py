"""Read the checked-in provider catalog without exposing credentials."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from packages.shared.config import settings


REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "source_registry.yaml"


def load_source_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        registry = yaml.safe_load(handle) or {}
    configured = {
        "tsetmc_authenticated_api": bool(settings.tsetmc_api_username and settings.tsetmc_api_password),
        "tindex_secondary": bool(settings.tindex_api_token),
        "bourseview_commercial": bool(settings.bourseview_api_token),
        "sourcearena_market_api": bool(settings.sourcearena_api_token),
        "brsapi_market_api": bool(settings.brsapi_api_key),
        "persianapi_market": bool(settings.persianapi_token),
        "api_ir_commercial": bool(settings.api_ir_token),
        "investats_custom_api": False,
    }
    for source in registry.get("sources", []):
        key = source.get("key")
        source["credential_configured"] = configured.get(key, False)
    return registry
