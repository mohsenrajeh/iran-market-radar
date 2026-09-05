"""Persistence and normalization for display-only market backup feeds."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from packages.domain.models import MarketDataBatch, ReferenceMarketObservation
from packages.shared.datetime_utils import now_utc
from packages.shared.persian import normalize_persian_text


def _float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def _int(value: Any) -> int:
    parsed = _float(value)
    return max(0, int(parsed or 0))


def normalize_brsapi_row(row: dict[str, Any], *, source_timestamp: datetime | None) -> dict[str, Any] | None:
    ticker = normalize_persian_text(str(row.get("l18") or "").strip())
    isin = str(row.get("isin") or "").strip()
    last_price = _float(row.get("pl"))
    close_price = _float(row.get("pc"))
    yesterday = _float(row.get("py"))
    if not ticker or not isin or not last_price or not close_price or not yesterday:
        return None
    return {
        "source_instrument_code": str(row.get("id") or "") or None,
        "isin": isin,
        "ticker": ticker,
        "name_fa": normalize_persian_text(str(row.get("l30") or ticker).strip()),
        "market": None,
        "source_timestamp": source_timestamp,
        "last_price": last_price,
        "close_price": close_price,
        "first_price": _float(row.get("pf")),
        "high_price": _float(row.get("pmax")),
        "low_price": _float(row.get("pmin")),
        "yesterday_price": yesterday,
        "allowed_min": _float(row.get("tmin")),
        "allowed_max": _float(row.get("tmax")),
        "volume": _int(row.get("tvol")),
        "value": _float(row.get("tval")) or 0.0,
        "trade_count": _int(row.get("tno")),
        "state": None,
        "pe": _float(row.get("pe")),
        "eps": _float(row.get("eps")),
        "market_cap": _float(row.get("mv")),
        "raw_json": {"sector": row.get("cs"), "provider_time": row.get("time")},
    }


def persist_reference_batch(
    db: Session,
    *,
    source_key: str,
    provider_name: str,
    schema_version: str,
    rows: Iterable[dict[str, Any]],
    source_timestamp: datetime | None,
    complete: bool,
    metadata: dict[str, Any] | None = None,
) -> MarketDataBatch:
    """Persist an immutable display-only batch; never promotes execution rows."""
    if source_timestamp and source_timestamp.tzinfo is None:
        source_timestamp = source_timestamp.replace(tzinfo=timezone.utc)
    accepted = list(rows)
    batch = MarketDataBatch(
        source_key=source_key,
        provider_name=provider_name,
        source_timestamp=source_timestamp,
        received_at=now_utc(),
        mode="reference_only",
        trust_tier="REFERENCE",
        trade_eligible=False,
        schema_version=schema_version,
        row_count=len(accepted),
        complete=complete,
        metadata_json=metadata or {},
    )
    db.add(batch)
    db.flush()
    db.add_all([
        ReferenceMarketObservation(batch_id=batch.id, source_key=source_key, **row)
        for row in accepted
    ])
    db.commit()
    return batch
