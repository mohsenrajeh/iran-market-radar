"""Ensemble Scorer & Persian Explanation Engine."""
from datetime import datetime, timedelta, timezone
from packages.domain.models import PublishedSignal
from packages.market_rules.queue_model import evaluate_execution_feasibility
from packages.ml.calibration import SignalProbabilityCalibrator
from packages.shared.datetime_utils import now_utc
from packages.strategies.base import CandidateResult, StrategyContext
from packages.strategies.registry import strategy_registry
from packages.shared.config import settings
from services.scorer.fundamental_gate import FundamentalGateEvidence


def assemble_published_signal(
    ctx: StrategyContext,
    candidates: list[CandidateResult],
    calibrator: SignalProbabilityCalibrator,
    cross_sectional_rank_pct: float = 85.0,
    data_quality_score: float = 0.0,
    sample_support_score: float = 0.0,
    fundamental_evidence: FundamentalGateEvidence | None = None,
) -> PublishedSignal | None:
    """
    Combines candidate signals from multiple strategies into a unified PublishedSignal.
    Strictly separates p_profit, signal_strength, confidence, and opportunity_score.
    """
    if not candidates:
        return None

    # 1. Strategy Votes & Reasons
    strategy_votes = []
    top_reasons_fa = []
    family_votes: dict[str, list[float]] = {}
    
    for cand in candidates:
        strategy_votes.append({
            "strategy": cand.strategy_key,
            "family": cand.family,
            "vote": cand.vote,
            "reason_fa": cand.reason_fa,
        })
        top_reasons_fa.append(cand.reason_fa)
        if cand.family not in {"composite", "unclassified"}:
            family_votes.setdefault(cand.family, []).append(cand.vote)

    family_max_votes = {family: max(votes) for family, votes in family_votes.items()}
    qualifying_families = {
        family: vote
        for family, vote in family_max_votes.items()
        if vote >= settings.strategy_engine.min_family_vote
    }
    bullish_strategy_count = sum(
        1 for cand in candidates
        if cand.family != "composite" and cand.vote >= settings.strategy_engine.min_family_vote
    )
    technical_gate_passed = (
        len(qualifying_families) >= settings.strategy_engine.min_independent_technical_families
        and bullish_strategy_count >= settings.strategy_engine.min_bullish_strategies
    )
    avg_family_vote = sum(qualifying_families.values()) / len(qualifying_families) if qualifying_families else 0.0
    agreement_bonus = min(0.12, max(0, len(qualifying_families) - 1) * 0.03)
    raw_ensemble_score = min(1.0, avg_family_vote + agreement_bonus)

    # 2. Probability Calibration (p_profit 0 to 1)
    calibration_available = bool(calibrator.is_fitted and calibrator.calibrator is not None)
    if calibration_available:
        p_profit = calibrator.predict_p_profit(raw_ensemble_score)
    else:
        # The persisted schema currently requires a numeric value. Zero is an
        # explicit fail-closed sentinel and can never satisfy the publication gate.
        p_profit = 0.0

    # 3. Execution Feasibility & Queue Risk
    close_price = ctx.features.get("close")
    if close_price is None or close_price <= 0 or ctx.allowed_min <= 0 or ctx.allowed_max <= 0:
        return None
    exec_check = evaluate_execution_feasibility(
        last_price=close_price,
        allowed_min=ctx.allowed_min,
        allowed_max=ctx.allowed_max,
        avg_daily_volume=int(ctx.features.get("avg_turnover_20d", 0.0) / max(1, close_price)),
    )

    risk_flags_fa = list(exec_check.risk_flags_fa)
    for cand in candidates:
        for rf in cand.risk_flags_fa:
            if rf not in risk_flags_fa:
                risk_flags_fa.append(rf)
    if not technical_gate_passed:
        risk_flags_fa.append(
            f"گیت تکنیکال رد شد: {len(qualifying_families)} خانواده مستقل و {bullish_strategy_count} استراتژی صعودی؛ "
            f"حداقل {settings.strategy_engine.min_independent_technical_families} خانواده و {settings.strategy_engine.min_bullish_strategies} استراتژی لازم است."
        )
    fundamental_gate_passed = bool(fundamental_evidence and fundamental_evidence.passed)
    if not fundamental_gate_passed:
        fundamental_reasons = fundamental_evidence.reasons_fa if fundamental_evidence else ("شواهد بنیادی ارائه نشده است.",)
        risk_flags_fa.extend(reason for reason in fundamental_reasons if reason not in risk_flags_fa)
    if not calibration_available:
        risk_flags_fa.append("مدل احتمال سود هنوز با دادهٔ خارج از نمونه کالیبره نشده است؛ سیگنال غیرقابل معامله است.")

    # 4. Confidence (0 to 100)
    # 0.25 sample_support + 0.25 data_quality + 0.30 model_agreement + 0.20 regime_support
    agreement_factor = min(1.0, len(qualifying_families) / max(1, settings.strategy_engine.min_independent_technical_families))
    regime_factor = 0.90 if ctx.market_regime == "risk_on" else (0.70 if ctx.market_regime == "neutral" else 0.40)
    
    confidence = 100.0 * min(1.0, (
        0.25 * min(1.0, max(0.0, sample_support_score / 100.0)) +
        0.25 * (data_quality_score / 100.0) +
        0.30 * agreement_factor +
        0.20 * regime_factor
    ))

    # 5. Signal Strength (0 to 100)
    signal_strength = float(cross_sectional_rank_pct)

    # 6. Opportunity Score (0 to 100)
    edge_comp = signal_strength / 100.0
    prob_comp = max(0.0, (p_profit - 0.50) / 0.50)
    exec_comp = (exec_check.fill_probability_score / 100.0)
    risk_comp = 0.90 if risk_flags_fa else 1.0

    fundamental_comp = (fundamental_evidence.score / 100.0) if fundamental_evidence else 0.0
    opportunity_score = 100.0 * (
        0.30 * edge_comp +
        0.20 * prob_comp +
        0.15 * (confidence / 100.0) +
        0.15 * exec_comp +
        0.10 * regime_factor +
        0.10 * fundamental_comp
    ) * risk_comp
    opportunity_score = round(max(0.0, min(100.0, opportunity_score)), 1)

    # Grade determination
    liquidity_score = round(min(100.0, max(0.0, ctx.features.get("avg_turnover_20d", 0.0) / 1e7)), 1)
    publication_gate_passed = (
        technical_gate_passed
        and fundamental_gate_passed
        and calibration_available
        and data_quality_score >= settings.strategy_engine.min_data_quality_score
        and liquidity_score >= settings.risk.min_liquidity_score
        and not exec_check.is_locked_limit_up
        and opportunity_score >= settings.strategy_engine.min_opportunity_score
        and confidence >= settings.strategy_engine.min_confidence
    )

    if publication_gate_passed and opportunity_score >= 85 and confidence >= 70:
        grade = "A+"
    elif publication_gate_passed and opportunity_score >= 78:
        grade = "A"
    elif publication_gate_passed and opportunity_score >= 68:
        grade = "B"
    else:
        grade = "C"

    # Best Entry & Exit Plan from primary candidate
    primary_cand = max(candidates, key=lambda c: c.vote)
    strategy_versions = [
        f"{candidate.strategy_key}@{registered.version if registered else 'UNVERSIONED'}"
        for candidate in candidates
        for registered in [strategy_registry.get(candidate.strategy_key)]
    ]
    entry_zone = {
        "low": primary_cand.entry_low,
        "high": primary_cand.entry_high,
        "max_chase": primary_cand.max_chase,
    }
    invalidation = {
        "price": primary_cand.stop_price,
        "type": "structure_atr",
        "reason_fa": "شکست ساختار حمایتی و فعال شدن حد ضرر مبتنی بر نوسان (ATR)",
    }
    exit_plan = {
        "type": "targets_plus_time_stop",
        "targets": primary_cand.target_prices,
        "time_stop_sessions": primary_cand.time_stop_sessions,
        "trailing_rule": "خروج در هدف دوم یا فعال شدن حد ضرر متحرک",
    }

    signal_id = f"sig_{ctx.symbol}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    return PublishedSignal(
        id=signal_id,
        instrument_id=ctx.instrument_id,
        symbol=ctx.symbol,
        name_fa=ctx.name_fa,
        market=ctx.market,
        sector=ctx.sector_name,
        as_of=now_utc(),
        horizon=ctx.horizon,
        direction="long",
        actionable=publication_gate_passed,
        grade=grade,
        opportunity_score=opportunity_score,
        p_profit=round(float(p_profit), 2),
        confidence=round(float(confidence), 1),
        signal_strength=round(float(signal_strength), 1),
        expected_return_pct=round(float(ctx.features["ret_5d"] * 100), 1) if "ret_5d" in ctx.features else None,
        expected_drawdown_pct=-round(float(ctx.features["atr_pct"] * 1.5), 1) if "atr_pct" in ctx.features else None,
        current_price=close_price,
        entry_zone=entry_zone,
        invalidation=invalidation,
        exit_plan=exit_plan,
        liquidity_score=liquidity_score,
        fill_probability_score=exec_check.fill_probability_score,
        data_quality=data_quality_score,
        regime=ctx.market_regime,
        strategy_votes=strategy_votes,
        top_reasons_fa=top_reasons_fa[:3],
        risk_flags_fa=risk_flags_fa,
        decision_components={
            "technical_gate": {
                "passed": technical_gate_passed,
                "qualifying_families": qualifying_families,
                "bullish_strategy_count": bullish_strategy_count,
                "minimum_families": settings.strategy_engine.min_independent_technical_families,
                "minimum_strategies": settings.strategy_engine.min_bullish_strategies,
            },
            "fundamental_gate": fundamental_evidence.to_dict() if fundamental_evidence else {"passed": False, "reasons_fa": ["شواهد بنیادی ارائه نشده است."]},
            "liquidity_gate": {
                "passed": liquidity_score >= settings.risk.min_liquidity_score,
                "score": liquidity_score,
                "minimum": settings.risk.min_liquidity_score,
            },
            "data_quality_gate": {
                "passed": data_quality_score >= settings.strategy_engine.min_data_quality_score,
                "score": data_quality_score,
                "minimum": settings.strategy_engine.min_data_quality_score,
            },
            "sample_support": {
                "score": sample_support_score,
                "minimum_history_sessions": settings.strategy_engine.min_history_sessions,
            },
            "calibration_gate": {
                "passed": calibration_available,
                "version": calibrator.model_version,
                "reason_fa": None if calibration_available else "کالیبراتور خارج از نمونه برازش نشده است.",
            },
        },
        model_version=calibrator.model_version if calibration_available else None,
        strategy_version="|".join(sorted(strategy_versions)) or "UNVERSIONED",
        calibration_version=calibrator.model_version,
        expires_at=now_utc() + timedelta(days=5),
    )
