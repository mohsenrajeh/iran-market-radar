"""Ensemble Scorer & Persian Explanation Engine."""
from datetime import datetime, timedelta, timezone
from packages.domain.models import PublishedSignal
from packages.market_rules.queue_model import evaluate_execution_feasibility
from packages.ml.calibration import SignalProbabilityCalibrator
from packages.shared.datetime_utils import now_utc
from packages.strategies.base import CandidateResult, StrategyContext


def assemble_published_signal(
    ctx: StrategyContext,
    candidates: list[CandidateResult],
    calibrator: SignalProbabilityCalibrator,
    cross_sectional_rank_pct: float = 85.0,
    data_quality_score: float = 95.0,
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
    combined_vote_sum = 0.0
    
    for cand in candidates:
        strategy_votes.append({
            "strategy": cand.strategy_key,
            "vote": cand.vote,
            "reason_fa": cand.reason_fa,
        })
        top_reasons_fa.append(cand.reason_fa)
        combined_vote_sum += cand.vote

    avg_raw_vote = combined_vote_sum / len(candidates)
    agreement_bonus = min(0.20, (len(candidates) - 1) * 0.06)
    raw_ensemble_score = min(1.0, avg_raw_vote + agreement_bonus)

    # 2. Probability Calibration (p_profit 0 to 1)
    p_profit = calibrator.predict_p_profit(raw_ensemble_score)

    # 3. Execution Feasibility & Queue Risk
    close_price = ctx.features.get("close", 1000.0)
    exec_check = evaluate_execution_feasibility(
        last_price=close_price,
        allowed_min=ctx.allowed_min,
        allowed_max=ctx.allowed_max,
        avg_daily_volume=int(ctx.features.get("avg_turnover_20d", 10_000_000) / max(1, close_price)),
    )

    risk_flags_fa = list(exec_check.risk_flags_fa)
    for cand in candidates:
        for rf in cand.risk_flags_fa:
            if rf not in risk_flags_fa:
                risk_flags_fa.append(rf)

    # 4. Confidence (0 to 100)
    # 0.25 sample_support + 0.25 data_quality + 0.30 model_agreement + 0.20 regime_support
    agreement_factor = min(1.0, len(candidates) / 3.0)
    regime_factor = 0.90 if ctx.market_regime == "risk_on" else (0.70 if ctx.market_regime == "neutral" else 0.40)
    
    confidence = 100.0 * min(1.0, (
        0.25 * 0.85 +
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

    opportunity_score = 100.0 * (
        0.30 * edge_comp +
        0.25 * prob_comp +
        0.15 * (confidence / 100.0) +
        0.15 * exec_comp +
        0.15 * regime_factor
    ) * risk_comp
    opportunity_score = round(max(0.0, min(100.0, opportunity_score)), 1)

    # Grade determination
    if opportunity_score >= 85 and confidence >= 70 and not exec_check.is_locked_limit_up:
        grade = "A+"
    elif opportunity_score >= 78:
        grade = "A"
    elif opportunity_score >= 68:
        grade = "B"
    else:
        grade = "C"

    # Best Entry & Exit Plan from primary candidate
    primary_cand = max(candidates, key=lambda c: c.vote)
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
        actionable=(not exec_check.is_locked_limit_up and opportunity_score >= 65),
        grade=grade,
        opportunity_score=opportunity_score,
        p_profit=round(float(p_profit), 2),
        confidence=round(float(confidence), 1),
        signal_strength=round(float(signal_strength), 1),
        expected_return_pct=round(float(ctx.features.get("ret_5d", 0.03) * 100), 1),
        expected_drawdown_pct=-round(float(ctx.features.get("atr_pct", 2.0) * 1.5), 1),
        current_price=close_price,
        entry_zone=entry_zone,
        invalidation=invalidation,
        exit_plan=exit_plan,
        liquidity_score=round(min(100.0, max(20.0, ctx.features.get("avg_turnover_20d", 1e8) / 1e7)), 1),
        fill_probability_score=exec_check.fill_probability_score,
        data_quality=data_quality_score,
        regime=ctx.market_regime,
        strategy_votes=strategy_votes,
        top_reasons_fa=top_reasons_fa[:3],
        risk_flags_fa=risk_flags_fa,
        strategy_version="2026.08.1",
        calibration_version="5d-isotonic-v1",
        expires_at=now_utc() + timedelta(days=5),
    )
