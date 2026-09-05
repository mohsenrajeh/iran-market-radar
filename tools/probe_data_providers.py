"""Safe provider connectivity probe that never prints credentials or tokens."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.shared.config import settings
from packages.data_adapters.sourcearena import SourceArenaAdapter


async def _request(name: str, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"provider": name}
    try:
        async with httpx.AsyncClient(
            timeout=8,
            follow_redirects=False,
            proxy=settings.data_http_proxy,
            trust_env=settings.data_http_trust_env,
        ) as client:
            response = await client.request(method, url, **kwargs)
        result.update({
            "network": "reachable",
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type", "")[:80],
        })
        if name == "TSETMC_AUTH" and "json" in result["content_type"].lower():
            try:
                payload = response.json()
                data = payload.get("Data") or payload.get("data") or {}
                result["authenticated"] = bool(
                    isinstance(payload, dict)
                    and payload.get("IsSuccess", payload.get("isSuccess", False))
                    and isinstance(data, dict)
                    and (data.get("Token") or data.get("token"))
                )
                result["message"] = str(payload.get("Message") or payload.get("message") or "")[:160]
            except Exception:
                result["schema"] = "invalid_json"
    except Exception as exc:
        result.update({"network": "blocked", "error": type(exc).__name__, "detail": str(exc)[:160]})
    return result


async def main() -> None:
    probes = [
        _request(
            "TSETMC_AUTH",
            "POST",
            "https://api.tsetmc.com/Account/Login",
            json={"Username": settings.tsetmc_api_username, "Password": settings.tsetmc_api_password},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) if settings.tsetmc_api_username and settings.tsetmc_api_password else asyncio.sleep(
            0, result={"provider": "TSETMC_AUTH", "credential_configured": False, "network": "not_tested"}
        ),
        _request(
            "TSETMC_CDN",
            "GET",
            "https://cdn.tsetmc.com/api/Index/GetIndexB1LastAll/SelectedIndexes/1",
            headers={"Accept": "application/json", "User-Agent": "IranMarketRadar/2.0 paper-only"},
        ),
        _request("TINDEX", "GET", "https://tindex.app/en/developers/"),
        _request("BOURSEVIEW", "GET", "https://api.bourseview.com/"),
        _request("SOURCEARENA_DOCS", "GET", "https://sourcearena.ir/وب-سرویس-api-بورس-فرابورس/"),
        _request("PERSIANAPI_DOCS", "GET", "https://workspace.persianapi.com/ps-15660528e0"),
    ]
    results = await asyncio.gather(*probes)
    if settings.sourcearena_api_token:
        previous_enabled = settings.sourcearena.enabled
        settings.sourcearena.enabled = True
        try:
            adapter = SourceArenaAdapter()
            rows = await adapter.fetch_market_rows()
            results.append({
                "provider": "SOURCEARENA_CONTRACT",
                "credential_configured": True,
                "network": "reachable" if rows else "unavailable",
                "schema_rows": len(rows),
                "error": adapter.last_error,
            })
        finally:
            settings.sourcearena.enabled = previous_enabled
    for result in results:
        if result["provider"] == "TSETMC_AUTH":
            result["credential_configured"] = bool(settings.tsetmc_api_username and settings.tsetmc_api_password)
    print(json.dumps({
        "transport": {
            "explicit_proxy_configured": bool(settings.data_http_proxy),
            "trust_environment_proxy": settings.data_http_trust_env,
        },
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
