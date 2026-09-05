"""Quantitative Learning, Post-Mortem, Research Queue, and Champion vs Challenger API routes."""
from collections import defaultdict
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from packages.domain.models import (
    ClosedTradeHistory,
    TradePostMortem,
    StructuredLesson,
    ExperimentProposal,
    SampleSufficiency,
    ProposalStatus,
    LessonCategory,
    BacktestRun,
    CalibrationArtifact,
)
from packages.domain.schemas import (
    LearningDashboardResponse,
    StrategyPerformanceDetail,
    StructuredLessonResponse,
    ExperimentProposalResponse,
    TradePostMortemResponse,
)
from packages.shared.database import get_sync_db
from packages.shared.datetime_utils import now_utc
from packages.strategies.registry import strategy_registry
from services.paper_broker.learning_engine import learning_engine
from apps.api.routes.auth import get_current_user
from services.paper_broker.campaign import get_active_campaign_portfolio
from services.scorer.calibration_store import (
    MIN_OOS_SAMPLES,
    MIN_TRAIN_SAMPLES,
    activate_candidate,
    train_candidate,
)

router = APIRouter(prefix="/learning", tags=["Strategy Learning & Research"])


class ProposalActionRequest(BaseModel):
    action: Literal["backtest", "oos_validate", "paper_challenger", "approve", "reject", "promote"]
    rejection_reason_fa: str | None = None


def _max_streak(trades: list[ClosedTradeHistory], *, winning: bool) -> int:
    current = maximum = 0
    for trade in sorted(trades, key=lambda item: item.closed_at):
        matched = trade.net_pnl > 0 if winning else trade.net_pnl < 0
        current = current + 1 if matched else 0
        maximum = max(maximum, current)
    return maximum


def _drawdown_contribution(strategy_trades: list[ClosedTradeHistory], all_trades: list[ClosedTradeHistory]) -> float | None:
    total_losses = abs(sum(min(0.0, trade.net_pnl) for trade in all_trades))
    if total_losses <= 0:
        return None
    strategy_losses = abs(sum(min(0.0, trade.net_pnl) for trade in strategy_trades))
    return round((strategy_losses / total_losses) * 100.0, 2)


@router.get("/dashboard", response_model=LearningDashboardResponse)
def get_learning_dashboard(db: Session = Depends(get_sync_db)):
    """Returns learning center executive overview and data sufficiency."""
    port = get_active_campaign_portfolio(db)
    portfolio_id = port.id if port else "__missing_campaign__"
    total_closed = db.query(ClosedTradeHistory).filter(ClosedTradeHistory.portfolio_id == portfolio_id).count()
    observed_regimes = {
        row[0] for row in db.query(ClosedTradeHistory.market_regime_at_entry)
        .filter(ClosedTradeHistory.portfolio_id == portfolio_id)
        .distinct().all()
        if row[0] not in {None, "", "unknown"}
    }
    proposals = (
        db.query(ExperimentProposal)
        .join(StructuredLesson, ExperimentProposal.source_lesson_id == StructuredLesson.id)
        .join(ClosedTradeHistory, StructuredLesson.trade_id == ClosedTradeHistory.id)
        .filter(ClosedTradeHistory.portfolio_id == portfolio_id)
        .all()
    )
    active_challengers = sum(1 for p in proposals if p.status == "PAPER_CHALLENGER")
    pending_exp = sum(1 for p in proposals if p.status in ["PROPOSED", "BACKTESTING", "OOS_TESTING"])
    rejected_exp = sum(1 for p in proposals if p.status == "REJECTED")

    completed_runs = db.query(BacktestRun).filter(BacktestRun.status == "COMPLETED").all()
    validated_strategy_keys = {run.strategy_key for run in completed_runs if (run.trade_count or 0) >= 20}
    strategies_under_review = {
        p.strategy_key for p in proposals
        if p.status in {"PROPOSED", "BACKTESTING", "OOS_TESTING", "PAPER_CHALLENGER"}
    }
    suff_enum, sufficiency_status = learning_engine.evaluate_sample_sufficiency(total_closed, len(observed_regimes))
    process_scores = [
        row[0] for row in db.query(TradePostMortem.process_quality_score)
        .join(ClosedTradeHistory, TradePostMortem.trade_id == ClosedTradeHistory.id)
        .filter(ClosedTradeHistory.portfolio_id == portfolio_id)
        .all() if row[0] is not None
    ]
    overall_health = round(sum(process_scores) / len(process_scores), 1) if process_scores else None
    champion_summary = (
        f"{len(validated_strategy_keys)} استراتژی دارای بک‌تست تکمیل‌شده با حداقل ۲۰ معامله است."
        if validated_strategy_keys
        else "هیچ نسخه‌ای هنوز شواهد کافی برای عنوان Champion ندارد."
    )

    minimum_tuning = MIN_TRAIN_SAMPLES + MIN_OOS_SAMPLES
    active_calibration = db.query(CalibrationArtifact).filter(CalibrationArtifact.status == "ACTIVE").first()
    if active_calibration:
        tuning_stage = "ACTIVE_VALIDATED_CURVE"
        tuning_stage_fa = "نسخه احتمال‌سنجی خارج‌نمونه فعال است"
        next_action_fa = "نتایج نسخه فعال را فقط روی معاملات جدید پایش کنید؛ بازآموزی روی همان نمونه ممنوع است."
    elif total_closed >= minimum_tuning and len(observed_regimes) >= 2:
        tuning_stage = "READY_FOR_CANDIDATE"
        tuning_stage_fa = "آماده ساخت نسخه آزمایشی"
        next_action_fa = "یک نسخه کاندید بسازید؛ فعال‌سازی فقط پس از بهبود Brier خارج‌نمونه ممکن است."
    else:
        tuning_stage = "COLLECTING_EVIDENCE"
        tuning_stage_fa = "در حال جمع‌آوری شواهد واقعی"
        next_action_fa = f"تا حداقل {minimum_tuning} معامله بسته در دو وضعیت بازار، هیچ پارامتر تولیدی تغییر نمی‌کند."

    return LearningDashboardResponse(
        total_closed_trades=total_closed,
        validated_strategies_count=len(validated_strategy_keys),
        strategies_under_review_count=len(strategies_under_review),
        active_challengers_count=active_challengers,
        pending_experiments_count=pending_exp,
        rejected_experiments_count=rejected_exp,
        data_sufficiency_status=sufficiency_status,
        champion_status_summary=champion_summary,
        overall_health_score=overall_health,
        tuning_stage=tuning_stage,
        tuning_stage_fa=tuning_stage_fa,
        minimum_closed_trades_for_tuning=minimum_tuning,
        observed_market_regimes=len(observed_regimes),
        next_action_fa=next_action_fa,
        automatic_promotion_enabled=False,
    )


@router.get("/strategies/performance", response_model=list[StrategyPerformanceDetail])
def get_strategies_learning_performance(db: Session = Depends(get_sync_db)):
    """Returns deep performance metrics and sample sufficiency for all 12 quantitative strategies."""
    all_strategies = strategy_registry.list_strategies()
    port = get_active_campaign_portfolio(db)
    trades = db.query(ClosedTradeHistory).filter(
        ClosedTradeHistory.portfolio_id == (port.id if port else "__missing_campaign__")
    ).all()

    trade_groups: dict[str, list[ClosedTradeHistory]] = {}
    for t in trades:
        trade_groups.setdefault(t.strategy_id, []).append(t)

    result = []
    for strat in all_strategies:
        s_trades = trade_groups.get(strat.key, [])
        n_count = len(s_trades)
        wins = [t for t in s_trades if t.net_pnl > 0]
        losses = [t for t in s_trades if t.net_pnl < 0]

        if n_count > 0:
            win_rate = (len(wins) / n_count) * 100.0
            avg_r = sum(t.realized_R for t in s_trades) / n_count
            r_sorted = sorted(t.realized_R for t in s_trades)
            median_r = r_sorted[len(r_sorted) // 2]
            avg_win_r = sum(t.realized_R for t in wins) / max(len(wins), 1)
            avg_loss_r = sum(t.realized_R for t in losses) / max(len(losses), 1)
            expectancy = ((len(wins) / n_count) * avg_win_r) + ((len(losses) / n_count) * avg_loss_r)
            profit_factor = (sum(t.net_pnl for t in wins) / abs(sum(t.net_pnl for t in losses))) if losses else None
            avg_mfe = sum(t.MFE for t in s_trades) / n_count
            avg_mae = sum(t.MAE for t in s_trades) / n_count
            avg_holding = sum(t.holding_sessions for t in s_trades) / n_count
            total_fees = sum(t.total_cost for t in s_trades) / 10.0
            total_slip = sum(t.slippage_cost for t in s_trades) / 10.0
        else:
            win_rate = avg_r = median_r = avg_win_r = avg_loss_r = None
            expectancy = profit_factor = avg_mfe = avg_mae = avg_holding = None
            total_fees = total_slip = 0.0

        regime_count = len({trade.market_regime_at_entry for trade in s_trades if trade.market_regime_at_entry not in {"", "unknown"}})
        suff_enum, suff_fa = learning_engine.evaluate_sample_sufficiency(n_count, regime_count)
        health_score = round(max(0.0, min(100.0, 50.0 + (expectancy or 0.0) * 20.0)), 1) if n_count >= 20 else None

        warnings = []
        if n_count < 20:
            warnings.append("حجم نمونه آماری کمتر از حداقل آستانه ۲۰ معامله است؛ به نتایج وزن مطلق ندهید.")
        if avg_mae is not None and avg_mae > 4.0:
            warnings.append("حداکثر نوسان نامطلوب (MAE) بالاتر از حد مطلوب است؛ استاپ‌ها را بازبینی کنید.")

        result.append(
            StrategyPerformanceDetail(
                strategy_id=strat.key,
                strategy_name_fa=strat.name_fa,
                strategy_version="v1.0",
                closed_trades=n_count,
                wins=len(wins),
                losses=len(losses),
                win_rate_pct=round(win_rate, 1) if win_rate is not None else None,
                net_expectancy=round(expectancy, 2) if expectancy is not None else None,
                avg_R=round(avg_r, 2) if avg_r is not None else None,
                median_R=round(median_r, 2) if median_r is not None else None,
                profit_factor=round(profit_factor, 2) if profit_factor is not None else None,
                avg_win_R=round(avg_win_r, 2) if avg_win_r is not None else None,
                avg_loss_R=round(avg_loss_r, 2) if avg_loss_r is not None else None,
                max_consecutive_losses=_max_streak(s_trades, winning=False),
                max_consecutive_wins=_max_streak(s_trades, winning=True),
                avg_MFE=round(avg_mfe, 1) if avg_mfe is not None else None,
                avg_MAE=round(avg_mae, 1) if avg_mae is not None else None,
                avg_holding_sessions=round(avg_holding, 1) if avg_holding is not None else None,
                drawdown_contribution_pct=_drawdown_contribution(s_trades, trades),
                total_fees_tomans=round(total_fees),
                total_slippage_tomans=round(total_slip),
                sample_sufficiency=suff_enum.value,
                sample_sufficiency_fa=suff_fa,
                health_score=health_score,
                health_status=("قابل ارزیابی" if health_score is not None else "نمونه ناکافی"),
                warnings=warnings,
            )
        )

    return result


@router.get("/calibration/artifacts")
def list_calibration_artifacts(db: Session = Depends(get_sync_db)):
    port = get_active_campaign_portfolio(db)
    if not port:
        return []
    artifacts = (
        db.query(CalibrationArtifact)
        .filter(CalibrationArtifact.portfolio_id == port.id)
        .order_by(CalibrationArtifact.created_at.desc())
        .limit(20).all()
    )
    return [{
        "id": item.id,
        "version": item.version,
        "status": item.status,
        "train_sample_size": item.train_sample_size,
        "oos_sample_size": item.oos_sample_size,
        "observed_regimes": item.observed_regimes,
        "brier_before": item.brier_before,
        "brier_after": item.brier_after,
        "ece_after": item.ece_after,
        "rejection_reason_fa": item.rejection_reason_fa,
        "created_at": item.created_at.isoformat(),
        "activated_at": item.activated_at.isoformat() if item.activated_at else None,
    } for item in artifacts]


@router.post("/calibration/train-candidate")
def train_calibration_candidate(
    db: Session = Depends(get_sync_db),
    current_user: dict = Depends(get_current_user),
):
    port = get_active_campaign_portfolio(db)
    if not port:
        raise HTTPException(status_code=409, detail="کمپین کاغذی فعال موجود نیست.")
    result = train_candidate(db, port.id)
    db.commit()
    if result.artifact is None:
        raise HTTPException(status_code=409, detail=result.reason_fa)
    return {
        "success": result.allowed,
        "message": result.reason_fa,
        "artifact_id": result.artifact.id,
        "status": result.artifact.status,
        "eligible_samples": result.eligible_samples,
        "observed_regimes": list(result.observed_regimes),
        "brier_before": result.artifact.brier_before,
        "brier_after": result.artifact.brier_after,
    }


@router.post("/calibration/{artifact_id}/activate")
def activate_calibration_candidate(
    artifact_id: str,
    db: Session = Depends(get_sync_db),
    current_user: dict = Depends(get_current_user),
):
    port = get_active_campaign_portfolio(db)
    artifact = db.query(CalibrationArtifact).filter(
        CalibrationArtifact.id == artifact_id,
        CalibrationArtifact.portfolio_id == (port.id if port else "__missing_campaign__"),
    ).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="نسخه تنظیم احتمال در کمپین فعال پیدا نشد.")
    try:
        activate_candidate(db, artifact, str(current_user.get("sub") or "system-owner"))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return {"success": True, "message": "نسخه تأییدشده فعال و نسخه قبلی آرشیو شد.", "version": artifact.version}


@router.get("/post-mortems", response_model=list[StructuredLessonResponse])
def get_post_mortems_feed(category: str | None = None, db: Session = Depends(get_sync_db)):
    """Returns structured lessons extracted from closed trades."""
    port = get_active_campaign_portfolio(db)
    query = (
        db.query(StructuredLesson)
        .join(ClosedTradeHistory, StructuredLesson.trade_id == ClosedTradeHistory.id)
        .filter(ClosedTradeHistory.portfolio_id == (port.id if port else "__missing_campaign__"))
        .order_by(StructuredLesson.created_at.desc())
    )
    if category:
        query = query.filter(StructuredLesson.category == category.upper())

    lessons = query.limit(50).all()
    return [
        StructuredLessonResponse(
            id=l.id,
            trade_id=l.trade_id,
            category=l.category,
            finding_fa=l.finding_fa,
            evidence_data=l.evidence_data or {},
            confidence_pct=l.confidence_pct,
            action_candidate_fa=l.action_candidate_fa,
            requires_validation=l.requires_validation,
            created_at=l.created_at.isoformat(),
        )
        for l in lessons
    ]


@router.get("/research-queue", response_model=list[ExperimentProposalResponse])
def get_research_queue(status: str | None = None, db: Session = Depends(get_sync_db)):
    """Returns research queue experiment proposals (Champion vs Challenger)."""
    port = get_active_campaign_portfolio(db)
    query = (
        db.query(ExperimentProposal)
        .join(StructuredLesson, ExperimentProposal.source_lesson_id == StructuredLesson.id)
        .join(ClosedTradeHistory, StructuredLesson.trade_id == ClosedTradeHistory.id)
        .filter(ClosedTradeHistory.portfolio_id == (port.id if port else "__missing_campaign__"))
        .order_by(ExperimentProposal.created_at.desc())
    )
    if status:
        query = query.filter(ExperimentProposal.status == status.upper())

    proposals = query.all()
    status_fa_map = {
        "PROPOSED": "پیشنهاد اولیه (در انتظار بک‌تست)",
        "BACKTESTING": "در حال اجرای شبیه‌ساز تاریخی",
        "OOS_TESTING": "ارزیابی خارج از نمونه (OOS)",
        "PAPER_CHALLENGER": "چالشگر فعال در پیپر تریدینگ",
        "APPROVED": "تصویب‌شده توسط کمیته ریسک",
        "PROMOTED": "ارتقا یافته به نسخه Champion",
        "REJECTED": "رد شده (با درج علت و حفظ تاریخچه)",
    }

    return [
        ExperimentProposalResponse(
            id=p.id,
            source_lesson_id=p.source_lesson_id,
            strategy_key=p.strategy_key,
            strategy_name_fa=p.strategy_name_fa,
            champion_version=p.champion_version,
            challenger_version=p.challenger_version,
            status=p.status,
            status_fa=status_fa_map.get(p.status, p.status),
            hypothesis_fa=p.hypothesis_fa,
            parameter_changes=p.parameter_changes or {},
            backtest_metrics=p.backtest_metrics or {},
            oos_metrics=p.oos_metrics or {},
            sample_sufficiency=p.sample_sufficiency,
            rejection_reason_fa=p.rejection_reason_fa,
            approved_by=p.approved_by,
            promoted_at=p.promoted_at.isoformat() if p.promoted_at else None,
            created_at=p.created_at.isoformat(),
        )
        for p in proposals
    ]


@router.post("/proposals/{proposal_id}/action")
def handle_proposal_action(
    proposal_id: str,
    req: ProposalActionRequest,
    db: Session = Depends(get_sync_db),
    current_user: dict = Depends(get_current_user),
):
    """Advances proposal lifecycle in the research queue. Production promotion requires explicit approval."""
    port = get_active_campaign_portfolio(db)
    prop = (
        db.query(ExperimentProposal)
        .join(StructuredLesson, ExperimentProposal.source_lesson_id == StructuredLesson.id)
        .join(ClosedTradeHistory, StructuredLesson.trade_id == ClosedTradeHistory.id)
        .filter(
            ExperimentProposal.id == proposal_id,
            ClosedTradeHistory.portfolio_id == (port.id if port else "__missing_campaign__"),
        )
        .first()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="فرضیه مورد نظر در صف تحقیقات یافت نشد.")

    allowed_from = {
        "backtest": {"PROPOSED"},
        "oos_validate": {"BACKTESTING"},
        "paper_challenger": {"OOS_TESTING"},
        "approve": {"PAPER_CHALLENGER"},
        "promote": {"APPROVED"},
        "reject": {"PROPOSED", "BACKTESTING", "OOS_TESTING", "PAPER_CHALLENGER", "APPROVED"},
    }
    if prop.status not in allowed_from[req.action]:
        raise HTTPException(status_code=409, detail=f"گذار {prop.status} به عملیات {req.action} مجاز نیست.")

    if req.action == "backtest":
        raise HTTPException(
            status_code=409,
            detail="این فرضیه هنوز تغییر پارامتر و اجرای بک‌تست ثبت‌شده ندارد؛ وضعیت آن به‌صورت نمایشی تغییر داده نشد.",
        )
    elif req.action == "oos_validate":
        raise HTTPException(
            status_code=409,
            detail="اجرای OOS برای این فرضیه به runner زمان‌محور و نتیجه ثبت‌شده نیاز دارد؛ وضعیت آن به‌صورت نمایشی تغییر داده نشد.",
        )
    elif req.action == "paper_challenger":
        if not prop.oos_metrics or int(prop.oos_metrics.get("oos_sample_size", 0)) < 20:
            raise HTTPException(status_code=409, detail="نتیجه OOS ثبت‌شده با حداقل ۲۰ نمونه برای تست کاغذی لازم است.")
        prop.status = "PAPER_CHALLENGER"
    elif req.action == "approve":
        if prop.sample_sufficiency != "STATISTICALLY_STABLE":
            raise HTTPException(status_code=409, detail="تأیید قبل از کفایت آماری مجاز نیست.")
        prop.status = "APPROVED"
        prop.approved_by = str(current_user.get("sub") or "authenticated-admin")
    elif req.action == "reject":
        prop.status = "REJECTED"
        prop.rejection_reason_fa = req.rejection_reason_fa or "تست خارج از نمونه (OOS) نشان‌دهنده برازش بیش‌ازحد (Overfitting) بود."
    elif req.action == "promote":
        if not prop.backtest_metrics or not prop.oos_metrics:
            raise HTTPException(status_code=409, detail="ارتقا بدون شواهد بک‌تست و OOS ثبت‌شده مجاز نیست.")
        prop.status = "PROMOTED"
        prop.promoted_at = now_utc()
        prop.approved_by = str(current_user.get("sub") or "authenticated-admin")

    db.commit()
    db.refresh(prop)

    return {
        "success": True,
        "message": f"وضعیت فرضیه به {prop.status} تغییر یافت.",
        "proposal_id": prop.id,
        "status": prop.status,
    }


@router.get("/breakdown/clusters")
def get_failure_and_success_clusters(db: Session = Depends(get_sync_db)):
    """Returns cluster diagnostics for failed and successful trades, plus holding period distributions."""
    port = get_active_campaign_portfolio(db)
    trades = db.query(ClosedTradeHistory).filter(
        ClosedTradeHistory.portfolio_id == (port.id if port else "__missing_campaign__")
    ).order_by(ClosedTradeHistory.closed_at.asc()).all()
    failed = [trade for trade in trades if trade.net_pnl < 0]
    successful = [trade for trade in trades if trade.net_pnl > 0]

    def grouped(rows: list[ClosedTradeHistory], key_fn, metric_name: str) -> list[dict]:
        groups: dict[str, list[ClosedTradeHistory]] = defaultdict(list)
        for row in rows:
            groups[key_fn(row)].append(row)
        output = []
        total = len(rows)
        for key, members in sorted(groups.items(), key=lambda item: len(item[1]), reverse=True):
            output.append({
                "title_fa": key,
                "count": len(members),
                "pct": round((len(members) / total) * 100.0, 1) if total else 0.0,
                metric_name: round(sum(item.realized_R for item in members) / len(members), 2),
                "evidence": "closed_trade_history",
            })
        return output

    buckets = [
        ("۱ تا ۳ روز", 1, 3),
        ("۴ تا ۷ روز", 4, 7),
        ("۸ تا ۱۵ روز", 8, 15),
        ("۱۶ تا ۳۰ روز", 16, 30),
        ("بیش از ۳۰ روز", 31, 10_000),
    ]
    holding = []
    for label, low, high in buckets:
        members = [trade for trade in trades if low <= trade.holding_sessions <= high]
        wins = [trade for trade in members if trade.net_pnl > 0]
        holding.append({
            "bucket": label,
            "trades_count": len(members),
            "win_rate": round((len(wins) / len(members)) * 100.0, 1) if members else None,
            "expectancy_R": round(sum(trade.realized_R for trade in members) / len(members), 2) if members else None,
        })
    return {
        "failed_clusters": grouped(failed, lambda row: row.exit_reason or "نامشخص", "avg_loss_R"),
        "success_clusters": grouped(successful, lambda row: row.strategy_name_fa or row.strategy_id, "avg_win_R"),
        "holding_period_buckets": holding,
    }
