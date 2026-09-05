"""Walk-forward calibration candidates and reversible database-backed activation."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from packages.domain.models import CalibrationArtifact, ClosedTradeHistory, DecisionAudit
from packages.ml.calibration import (
    SignalProbabilityCalibrator,
    calculate_brier_score,
    calculate_ece,
)
from packages.shared.datetime_utils import now_utc


MIN_TRAIN_SAMPLES = 50
MIN_OOS_SAMPLES = 20


@dataclass(frozen=True)
class CalibrationTrainingResult:
    artifact: CalibrationArtifact | None
    allowed: bool
    reason_fa: str
    eligible_samples: int
    observed_regimes: tuple[str, ...]


def load_active_calibrator(db: Session) -> SignalProbabilityCalibrator:
    artifact = (
        db.query(CalibrationArtifact)
        .filter(CalibrationArtifact.status == "ACTIVE")
        .order_by(CalibrationArtifact.activated_at.desc())
        .first()
    )
    if artifact is None:
        return SignalProbabilityCalibrator(method="isotonic")
    return SignalProbabilityCalibrator.from_isotonic_curve(
        list(artifact.x_thresholds or []),
        list(artifact.y_thresholds or []),
        model_version=artifact.version,
    )


def train_candidate(db: Session, portfolio_id: str) -> CalibrationTrainingResult:
    trades = (
        db.query(ClosedTradeHistory)
        .filter(ClosedTradeHistory.portfolio_id == portfolio_id)
        .order_by(ClosedTradeHistory.opened_at.asc(), ClosedTradeHistory.id.asc())
        .all()
    )
    samples: list[tuple[ClosedTradeHistory, float, int]] = []
    for trade in trades:
        if not trade.decision_id:
            continue
        decision = db.query(DecisionAudit).filter(DecisionAudit.id == trade.decision_id).first()
        if decision is None or not 0.0 <= decision.opportunity_score <= 100.0:
            continue
        samples.append((trade, decision.opportunity_score / 100.0, 1 if trade.net_pnl > 0 else 0))

    regimes = tuple(sorted({trade.market_regime_at_entry for trade, _, _ in samples if trade.market_regime_at_entry not in {"", "unknown"}}))
    minimum_total = MIN_TRAIN_SAMPLES + MIN_OOS_SAMPLES
    if len(samples) < minimum_total:
        return CalibrationTrainingResult(
            None, False,
            f"برای تنظیم احتمال سود حداقل {minimum_total} معامله قابل‌ردیابی لازم است؛ اکنون {len(samples)} نمونه موجود است.",
            len(samples), regimes,
        )
    if len(regimes) < 2:
        return CalibrationTrainingResult(
            None, False,
            "نمونه‌ها باید حداقل دو وضعیت متفاوت بازار را پوشش دهند.",
            len(samples), regimes,
        )

    split_at = max(MIN_TRAIN_SAMPLES, len(samples) - MIN_OOS_SAMPLES)
    train_rows = samples[:split_at]
    oos_rows = samples[split_at:]
    train_scores = np.asarray([row[1] for row in train_rows], dtype=float)
    train_labels = np.asarray([row[2] for row in train_rows], dtype=int)
    oos_scores = np.asarray([row[1] for row in oos_rows], dtype=float)
    oos_labels = np.asarray([row[2] for row in oos_rows], dtype=int)
    if len(set(train_labels.tolist())) < 2:
        return CalibrationTrainingResult(
            None, False,
            "پنجره آموزش باید هم معامله سودده و هم زیان‌ده داشته باشد.",
            len(samples), regimes,
        )

    calibrator = SignalProbabilityCalibrator(method="isotonic").fit(train_scores, train_labels)
    calibrated_oos = np.asarray([calibrator.predict_p_profit(float(score)) for score in oos_scores])
    brier_before = float(calculate_brier_score(oos_scores, oos_labels) or 0.0)
    brier_after = float(calculate_brier_score(calibrated_oos, oos_labels) or 0.0)
    ece_after = calculate_ece(calibrated_oos, oos_labels)
    x_thresholds, y_thresholds = calibrator.export_isotonic_curve()
    fingerprint_source = "|".join(
        f"{trade.id}:{trade.closed_at.isoformat()}:{label}"
        for trade, _, label in samples
    )
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
    version = f"isotonic-oos-{fingerprint[:12]}"
    existing = db.query(CalibrationArtifact).filter(CalibrationArtifact.version == version).first()
    if existing is not None:
        return CalibrationTrainingResult(
            existing,
            existing.status in {"CANDIDATE", "ACTIVE"},
            "برای همین دیتاست قبلاً نسخه تنظیم احتمال ثبت شده است.",
            len(samples), regimes,
        )
    improved = brier_after < brier_before
    artifact = CalibrationArtifact(
        version=version,
        method="isotonic",
        status="CANDIDATE" if improved else "REJECTED",
        portfolio_id=portfolio_id,
        dataset_fingerprint=fingerprint,
        train_sample_size=len(train_rows),
        oos_sample_size=len(oos_rows),
        observed_regimes=list(regimes),
        x_thresholds=x_thresholds,
        y_thresholds=y_thresholds,
        brier_before=brier_before,
        brier_after=brier_after,
        ece_after=ece_after,
        rejection_reason_fa=None if improved else "کالیبراسیون جدید روی داده خارج‌نمونه Brier را بهتر نکرد.",
    )
    db.add(artifact)
    db.flush()
    return CalibrationTrainingResult(
        artifact,
        improved,
        "نسخه کاندید فقط برای بازبینی ثبت شد؛ فعال‌سازی خودکار انجام نشد." if improved else artifact.rejection_reason_fa,
        len(samples), regimes,
    )


def activate_candidate(db: Session, artifact: CalibrationArtifact, approved_by: str) -> None:
    if artifact.status != "CANDIDATE":
        raise ValueError("Only a passing calibration candidate can be activated.")
    if artifact.oos_sample_size < MIN_OOS_SAMPLES or artifact.brier_after >= artifact.brier_before:
        raise ValueError("Candidate does not satisfy the out-of-sample improvement gate.")
    for active in db.query(CalibrationArtifact).filter(CalibrationArtifact.status == "ACTIVE").all():
        active.status = "ARCHIVED"
    artifact.status = "ACTIVE"
    artifact.activated_at = now_utc()
    artifact.approved_by = approved_by
