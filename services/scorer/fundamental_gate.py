"""Point-in-time fundamental eligibility gate backed by independent source receipts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from packages.domain.models import DataSourceReceipt, Filing, FundamentalSnapshot
from packages.shared.config import settings
from services.collector.quality import healthy_fundamental_receipts, fundamental_independence_key


@dataclass(frozen=True)
class FundamentalGateEvidence:
    passed: bool
    source_keys: tuple[str, ...]
    provider_names: tuple[str, ...]
    score: float
    as_of_utc: str | None
    reasons_fa: tuple[str, ...]
    metrics: dict

    def to_dict(self) -> dict:
        result = asdict(self)
        result["source_keys"] = list(self.source_keys)
        result["provider_names"] = list(self.provider_names)
        result["reasons_fa"] = list(self.reasons_fa)
        return result


def evaluate_fundamental_gate(db: Session, instrument_id: str, symbol: str, *, decision_time: datetime | None = None) -> FundamentalGateEvidence:
    decision_time = decision_time or datetime.now(timezone.utc)
    if decision_time.tzinfo is None:
        decision_time = decision_time.replace(tzinfo=timezone.utc)
    receipts = healthy_fundamental_receipts(db, decision_time=decision_time)
    receipt_by_source = {receipt.source_key: receipt for receipt in receipts}
    reasons: list[str] = []
    snapshot = (
        db.query(FundamentalSnapshot)
        .filter(FundamentalSnapshot.instrument_id == instrument_id, FundamentalSnapshot.as_of <= decision_time)
        .order_by(FundamentalSnapshot.as_of.desc())
        .first()
    )
    if snapshot is None:
        reasons.append("snapshot بنیادی point-in-time برای نماد موجود نیست.")
        return FundamentalGateEvidence(False, (), (), 0.0, None, tuple(reasons), {})

    snapshot_sources = tuple(sorted(set((snapshot.details or {}).get("source_keys") or [])))
    matched_receipts = [receipt_by_source[key] for key in snapshot_sources if key in receipt_by_source]
    source_keys = tuple(sorted(receipt.source_key for receipt in matched_receipts))
    provider_names = tuple(sorted({receipt.provider_name for receipt in matched_receipts}))
    independence_keys = {fundamental_independence_key(receipt) for receipt in matched_receipts}
    if not snapshot_sources:
        reasons.append("provenance منابع در snapshot بنیادی ثبت نشده است.")
    missing_receipts = sorted(set(snapshot_sources) - set(receipt_by_source))
    if missing_receipts:
        reasons.append("receipt سالم پیش از زمان تصمیم برای این منابع موجود نیست: " + "، ".join(missing_receipts))
    if len(independence_keys) < settings.minimum_fundamental_sources:
        reasons.append(
            f"حداقل {settings.minimum_fundamental_sources} خانواده upstream مستقل برای همین snapshot لازم است؛ اکنون {len(independence_keys)} خانواده موجود است."
        )

    as_of = snapshot.as_of
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    age_days = (decision_time - as_of.astimezone(timezone.utc)).days
    if age_days > 120:
        reasons.append(f"snapshot بنیادی {age_days} روزه و خارج از پنجره ۱۲۰روزه است.")
    if snapshot.fundamental_score < 60:
        reasons.append("امتیاز بنیادی کمتر از ۶۰ است.")
    if snapshot.piotroski_f_score < 5:
        reasons.append("امتیاز Piotroski کمتر از ۵ است.")
    if snapshot.monthly_sales_growth_yoy <= 0:
        reasons.append("رشد فروش سالانه ماهانه مثبت نیست.")
    if snapshot.debt_to_equity < 0 or snapshot.debt_to_equity > 2.5:
        reasons.append("نسبت بدهی به حقوق صاحبان سهام خارج از دامنه محافظه‌کارانه است.")

    filing = (
        db.query(Filing)
        .filter(
            Filing.instrument_id == instrument_id,
            Filing.symbol == symbol,
            Filing.published_at <= decision_time,
            Filing.structured_data["source_key"].as_string() == "codal_disclosures",
        )
        .order_by(Filing.published_at.desc())
        .first()
    )
    codal_receipt = receipt_by_source.get("codal_disclosures")
    if codal_receipt is None:
        reasons.append("receipt تازه و رسمی کدال پیش از زمان تصمیم وجود ندارد.")
    if filing is None:
        reasons.append("اطلاعیه کدال قابل ردیابی پیش از زمان تصمیم وجود ندارد.")
    elif filing.sentiment == "negative" and filing.impact_score >= 7:
        reasons.append("اطلاعیه منفی با اثر بالا در گیت کدال فعال است.")

    metrics = {
        "fundamental_score": snapshot.fundamental_score,
        "piotroski_f_score": snapshot.piotroski_f_score,
        "monthly_sales_growth_yoy": snapshot.monthly_sales_growth_yoy,
        "debt_to_equity": snapshot.debt_to_equity,
        "p_e_ratio": snapshot.p_e_ratio,
        "sector_p_e": snapshot.sector_p_e,
        "age_days": age_days,
        "latest_filing_id": filing.source_filing_id if filing else None,
        "source_keys": list(source_keys),
        "independence_keys": sorted(independence_keys),
    }
    return FundamentalGateEvidence(
        passed=not reasons,
        source_keys=source_keys,
        provider_names=provider_names,
        score=float(snapshot.fundamental_score),
        as_of_utc=as_of.astimezone(timezone.utc).isoformat(),
        reasons_fa=tuple(reasons or ["گیت بنیادی و کدال با شواهد point-in-time تأیید شد."]),
        metrics=metrics,
    )
