"""Evidence-based market/fundamental freshness gates for paper trading."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from packages.domain.models import DataSourceReceipt, Instrument, MarketSnapshot, MarketDataBatch
from packages.market_rules.trading_hours import is_tse_market_open
from packages.shared.config import settings
from services.collector.trusted_queries import trusted_market_snapshot_base_query


def instrument_data_quality_score(bars: list, client_rows: list) -> float:
    """Measured per-symbol completeness; never award a perfect score from a provider flag alone."""
    if not bars:
        return 0.0
    required_history = max(1, settings.strategy_engine.min_history_sessions)
    history_ratio = min(1.0, len(bars) / required_history)
    valid_bars = sum(
        1 for bar in bars
        if min(float(bar.open), float(bar.high), float(bar.low), float(bar.close), float(bar.last)) > 0
        and float(bar.high) >= float(bar.low)
        and int(bar.volume) >= 0
        and float(bar.value) >= 0
    )
    integrity_ratio = valid_bars / len(bars)
    bar_dates = {bar.trading_date for bar in bars}
    covered_client_dates = {row.trading_date for row in client_rows if row.trading_date in bar_dates}
    client_ratio = len(covered_client_dates) / len(bar_dates)
    return round(100.0 * (0.50 * history_ratio + 0.30 * integrity_ratio + 0.20 * client_ratio), 1)


def fundamental_independence_key(receipt: DataSourceReceipt) -> str:
    metadata = receipt.metadata_json or {}
    return str(metadata.get("independence_key") or metadata.get("upstream_family") or receipt.provider_name).strip()


def healthy_fundamental_receipts(db: Session, *, decision_time: datetime | None = None) -> list[DataSourceReceipt]:
    cutoff = _as_utc(decision_time) if decision_time else datetime.now(timezone.utc)
    freshness_cutoff = cutoff - timedelta(seconds=settings.quality.fundamental_receipt_stale_seconds)
    return (
        db.query(DataSourceReceipt)
        .filter(
            DataSourceReceipt.source_kind == "fundamental",
            DataSourceReceipt.status == "HEALTHY",
            DataSourceReceipt.mode == "official",
            DataSourceReceipt.last_success_at.isnot(None),
            DataSourceReceipt.last_success_at <= cutoff,
            DataSourceReceipt.last_success_at >= freshness_cutoff,
        )
        .all()
    )


@dataclass(frozen=True)
class DataGateDecision:
    allowed: bool
    status: str
    reasons_fa: tuple[str, ...]
    market_age_seconds: int | None
    official_fundamental_sources: int
    fixture_instruments: int
    evaluated_at_utc: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["reasons_fa"] = list(self.reasons_fa)
        return data


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def evaluate_data_gate(db: Session, *, require_market_open: bool = True) -> DataGateDecision:
    """Allow entries only with fresh official market data and independent fundamentals."""
    now = datetime.now(timezone.utc)
    reasons: list[str] = []
    fixture_count = (
        db.query(Instrument)
        .filter(Instrument.is_active == True, Instrument.source_instrument_code.like("INS\\_%", escape="\\"))
        .count()
    )
    if settings.market_data_mode != "official":
        reasons.append("حالت منبع داده رسمی نیست.")
    if fixture_count:
        reasons.append("دیتابیس شامل نمادهای fixture است و با داده رسمی قابل اختلاط نیست.")

    latest_snapshot = trusted_market_snapshot_base_query(db).order_by(
        MarketSnapshot.source_timestamp.desc()
    ).first()
    latest_market_at = latest_snapshot.source_timestamp if latest_snapshot else None
    market_age = None
    if latest_market_at is None:
        reasons.append("هیچ snapshot لحظه‌ای دارای provenance رسمی ثبت نشده است.")
    else:
        market_age = max(0, int((now - _as_utc(latest_market_at)).total_seconds()))
        if market_age > settings.quality.critical_market_stale_seconds:
            reasons.append(
                f"داده لحظه‌ای بازار {market_age} ثانیه قدمت دارد و از حد مجاز بیشتر است."
            )

    market_receipt = (
        db.query(DataSourceReceipt)
        .filter(DataSourceReceipt.source_key == "tsetmc_market_watch")
        .first()
    )
    if not market_receipt or market_receipt.status != "HEALTHY" or market_receipt.mode != "official":
        reasons.append("receipt سالم از market-watch رسمی TSETMC وجود ندارد.")
    latest_batch = db.get(MarketDataBatch, latest_snapshot.batch_id) if latest_snapshot else None
    if latest_market_at and latest_batch is None:
        reasons.append("batch رسمی کامل و متصل به snapshotهای جاری موجود نیست.")

    fundamental_sources = len({fundamental_independence_key(item) for item in healthy_fundamental_receipts(db, decision_time=now)})
    if fundamental_sources < settings.minimum_fundamental_sources:
        reasons.append(
            f"فقط {fundamental_sources} منبع بنیادی رسمی سالم است؛ حداقل {settings.minimum_fundamental_sources} منبع مستقل لازم است."
        )

    if require_market_open and not is_tse_market_open():
        reasons.append("بازار تهران اکنون خارج از جلسه معاملات پیوسته ۰۹:۰۰ تا ۱۲:۳۰ است.")

    return DataGateDecision(
        allowed=not reasons,
        status="HEALTHY" if not reasons else "BLOCKED",
        reasons_fa=tuple(reasons),
        market_age_seconds=market_age,
        official_fundamental_sources=fundamental_sources,
        fixture_instruments=fixture_count,
        evaluated_at_utc=now.isoformat(),
    )
