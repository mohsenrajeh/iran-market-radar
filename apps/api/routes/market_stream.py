"""Internal WebSocket stream for direct CDN market-cycle notifications."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from packages.shared.datetime_utils import now_utc, to_utc_iso
from services.collector.live_hub import market_live_hub

router = APIRouter(prefix="/market", tags=["market-stream"])


@router.websocket("/ws")
async def market_websocket(websocket: WebSocket):
    await websocket.accept()
    queue = market_live_hub.subscribe()
    await websocket.send_json({
        "type": "connected",
        "provider": "TSETMC_PUBLIC_CDN",
        "server_time_utc": to_utc_iso(now_utc()),
    })
    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30)
            except asyncio.TimeoutError:
                message = {"type": "heartbeat", "server_time_utc": to_utc_iso(now_utc())}
            await websocket.send_json(message)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        market_live_hub.unsubscribe(queue)
