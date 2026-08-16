"""Market regime classification for Iranian equity markets."""
from dataclasses import dataclass


@dataclass
class MarketRegimeResult:
    regime_label: str       # risk_on, risk_off, neutral, distribution
    regime_label_fa: str
    breadth_score: float    # 0 to 100 (% of stocks above 20 EMA or advancing)
    turnover_ratio: float   # Current vs 20-day median market turnover
    confidence: float       # 0 to 100


def classify_market_regime(
    advancers: int,
    decliners: int,
    stocks_above_ema20_pct: float,
    current_turnover: float,
    median_turnover_20d: float,
    index_ret_5d: float,
) -> MarketRegimeResult:
    """
    Evaluates market-wide conditions to determine market state.
    """
    total = max(1, advancers + decliners)
    adv_ratio = advancers / total
    turnover_ratio = current_turnover / max(1.0, median_turnover_20d)

    breadth_score = round(stocks_above_ema20_pct, 1)

    if adv_ratio > 0.60 and index_ret_5d > 0.01 and breadth_score > 55.0:
        regime = "risk_on"
        regime_fa = "رونق و تقاضای پرقدرت (ریسک‌پذیر)"
        conf = 85.0
    elif adv_ratio < 0.35 and index_ret_5d < -0.01 and breadth_score < 40.0:
        regime = "risk_off"
        regime_fa = "رکود و فشار عرضه (ریسک‌گریز)"
        conf = 80.0
    elif turnover_ratio > 1.4 and adv_ratio < 0.45:
        regime = "distribution"
        regime_fa = "توزیع و خروج نقدینگی در حجم بالا"
        conf = 75.0
    else:
        regime = "neutral"
        regime_fa = "متعادل و نوسانی"
        conf = 70.0

    return MarketRegimeResult(
        regime_label=regime,
        regime_label_fa=regime_fa,
        breadth_score=breadth_score,
        turnover_ratio=round(turnover_ratio, 2),
        confidence=conf,
    )
