"""Tests for Fundamental Analysis Engine and Piotroski F-Score."""
import pytest
from packages.fundamental_engine.metrics import (
    compute_piotroski_f_score,
    compute_valuation_multiples,
    evaluate_fundamental_score,
)


def test_piotroski_f_score_healthy_company():
    """Verify strong company gets a high Piotroski score (8-9)."""
    healthy_data = {
        "roa_pct": 35.0,
        "roa_prior_pct": 28.0,
        "cfo_rials": 150_000_000_000.0,
        "net_income_rials": 120_000_000_000.0,
        "debt_to_equity": 0.35,
        "debt_to_equity_prior": 0.45,
        "current_ratio": 1.75,
        "current_ratio_prior": 1.50,
        "shares_diluted": False,
        "gross_margin_pct": 32.0,
        "gross_margin_prior_pct": 29.0,
        "asset_turnover": 0.95,
        "asset_turnover_prior": 0.85,
    }
    score = compute_piotroski_f_score(healthy_data)
    assert score == 9, f"Expected perfect score 9, got {score}"


def test_piotroski_f_score_distressed_company():
    """Verify distressed/loss-making company gets low Piotroski score (0-3)."""
    weak_data = {
        "roa_pct": -5.0,
        "roa_prior_pct": 2.0,
        "cfo_rials": -20_000_000_000.0,
        "net_income_rials": -15_000_000_000.0,
        "debt_to_equity": 2.50,
        "debt_to_equity_prior": 1.80,
        "current_ratio": 0.75,
        "current_ratio_prior": 0.90,
        "shares_diluted": True,
        "gross_margin_pct": 8.0,
        "gross_margin_prior_pct": 12.0,
        "asset_turnover": 0.40,
        "asset_turnover_prior": 0.55,
    }
    score = compute_piotroski_f_score(weak_data)
    assert score <= 2, f"Expected score <= 2, got {score}"


def test_valuation_multiples():
    """Verify P/E, P/S, P/B, and Dividend yield calculation."""
    res = compute_valuation_multiples(
        price=10000.0,
        eps=2000.0,
        sales_per_share=5000.0,
        book_value_per_share=4000.0,
        dps=1200.0,
        sector_p_e=7.5,
    )
    assert res["p_e_ratio"] == 5.0
    assert res["p_s_ratio"] == 2.0
    assert res["p_b_ratio"] == 2.5
    assert res["dividend_yield"] == 12.0
    assert res["sector_p_e"] == 7.5


def test_evaluate_fundamental_score_top_pick():
    """Verify high ROE + low P/E results in A+ grade and undervalued verdict."""
    res = evaluate_fundamental_score(
        p_e=4.8,
        sector_p_e=7.2,
        p_s=1.5,
        roe_pct=42.0,
        net_margin_pct=32.0,
        sales_growth_yoy=55.0,
        piotroski_score=8,
        debt_to_equity=0.35,
    )
    assert res["fundamental_score"] >= 80.0
    assert res["fundamental_grade"] in ["A+", "A"]
    assert res["valuation_status"] == "undervalued"
    assert "حباب منفی" in res["valuation_status_fa"]
