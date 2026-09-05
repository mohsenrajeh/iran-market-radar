import numpy as np

from packages.ml.calibration import SignalProbabilityCalibrator
from packages.strategies.base import CandidateResult, StrategyContext
from services.scorer.ensemble import assemble_published_signal
from services.scorer.fundamental_gate import FundamentalGateEvidence


def _candidate(key: str, family: str, vote: float = 0.95) -> CandidateResult:
    return CandidateResult(
        strategy_key=key,
        family=family,
        vote=vote,
        raw_score=vote,
        entry_low=10_000,
        entry_high=10_100,
        max_chase=10_150,
        stop_price=9_500,
        target_prices=[11_500],
        time_stop_sessions=7,
        reason_fa=f"تأیید مستقل {family}",
        risk_flags_fa=[],
    )


def _context() -> StrategyContext:
    return StrategyContext(
        symbol="TEST",
        instrument_id="inst_test",
        name_fa="نماد آزمون",
        market="TSE",
        sector_name="آزمون",
        horizon="5d",
        features={"close": 10_000, "avg_turnover_20d": 2_000_000_000, "ret_5d": 0.08, "atr_pct": 2.0},
        market_regime="risk_on",
        allowed_min=9_500,
        allowed_max=10_500,
    )


def _fundamental(passed: bool = True) -> FundamentalGateEvidence:
    return FundamentalGateEvidence(
        passed=passed,
        source_keys=("codal_disclosures", "issuer_financials"),
        provider_names=("CODAL_SEO", "TSETMC"),
        score=90.0,
        as_of_utc="2026-08-16T09:00:00+00:00",
        reasons_fa=("گیت بنیادی تأیید شد." if passed else "گیت بنیادی رد شد.",),
        metrics={"piotroski_f_score": 8, "monthly_sales_growth_yoy": 35.0},
    )


def _fitted_calibrator() -> SignalProbabilityCalibrator:
    scores = np.linspace(0.05, 0.95, 100)
    labels = (scores >= 0.50).astype(int)
    return SignalProbabilityCalibrator().fit(scores, labels)


def test_actionable_requires_independent_families_and_fundamentals():
    candidates = [
        _candidate("trend_a", "trend"),
        _candidate("breakout_a", "breakout_volatility"),
        _candidate("smart_a", "smart_money"),
        _candidate("relative_a", "relative_strength"),
    ]
    signal = assemble_published_signal(
        _context(), candidates, _fitted_calibrator(),
        cross_sectional_rank_pct=99.0, data_quality_score=100.0,
        fundamental_evidence=_fundamental(True),
    )
    assert signal is not None
    assert signal.actionable is True
    assert signal.decision_components["technical_gate"]["passed"] is True
    assert signal.decision_components["fundamental_gate"]["passed"] is True
    assert signal.decision_components["calibration_gate"]["passed"] is True


def test_correlated_strategy_count_does_not_fake_family_confluence():
    candidates = [_candidate(f"trend_{idx}", "trend") for idx in range(8)]
    signal = assemble_published_signal(
        _context(), candidates, _fitted_calibrator(),
        cross_sectional_rank_pct=99.0, data_quality_score=100.0,
        fundamental_evidence=_fundamental(True),
    )
    assert signal is not None
    assert signal.actionable is False
    assert signal.decision_components["technical_gate"]["qualifying_families"] == {"trend": 0.95}


def test_fundamental_failure_blocks_otherwise_strong_technical_signal():
    candidates = [
        _candidate("trend_a", "trend"),
        _candidate("trend_b", "trend"),
        _candidate("breakout_a", "breakout_volatility"),
        _candidate("smart_a", "smart_money"),
    ]
    signal = assemble_published_signal(
        _context(), candidates, _fitted_calibrator(),
        cross_sectional_rank_pct=99.0, data_quality_score=100.0,
        fundamental_evidence=_fundamental(False),
    )
    assert signal is not None
    assert signal.actionable is False
    assert signal.decision_components["fundamental_gate"]["passed"] is False


def test_unfitted_probability_model_blocks_publication():
    candidates = [
        _candidate("trend_a", "trend"),
        _candidate("breakout_a", "breakout_volatility"),
        _candidate("smart_a", "smart_money"),
        _candidate("relative_a", "relative_strength"),
    ]
    signal = assemble_published_signal(
        _context(), candidates, SignalProbabilityCalibrator(),
        cross_sectional_rank_pct=99.0, data_quality_score=100.0,
        fundamental_evidence=_fundamental(True),
    )
    assert signal is not None
    assert signal.actionable is False
    assert signal.p_profit == 0.0
    assert signal.decision_components["calibration_gate"]["passed"] is False
