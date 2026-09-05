"""Market regime classification for Iranian equity markets."""
from dataclasses import dataclass
from datetime import timedelta
from statistics import median


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


def compute_market_regime_from_db(db) -> MarketRegimeResult | None:
    """Compute a PIT regime from persisted official snapshots and EOD history."""
    from packages.domain.models import EODBar, Instrument, MarketSnapshot
    from packages.shared.config import settings
    from packages.shared.datetime_utils import now_utc
    from services.collector.trusted_queries import (
        trusted_eod_query,
        trusted_market_snapshot_base_query,
    )

    instruments = db.query(Instrument).filter(Instrument.is_active == True).all()
    if not instruments:
        return None
    latest_snapshots = {}
    fresh_cutoff = now_utc() - timedelta(seconds=settings.quality.critical_market_stale_seconds)
    for snapshot in trusted_market_snapshot_base_query(db).filter(
        MarketSnapshot.source_timestamp >= fresh_cutoff
    ).order_by(
        MarketSnapshot.source_timestamp.desc()
    ).all():
        latest_snapshots.setdefault(snapshot.instrument_id, snapshot)
    if len(latest_snapshots) / max(1, len(instruments)) < settings.quality.minimum_symbol_completeness_ratio:
        return None

    advancers = 0
    decliners = 0
    above_ema20 = 0
    eligible_ema = 0
    returns_5d: list[float] = []
    daily_turnover: dict[object, float] = {}
    current_turnover = 0.0
    for instrument in instruments:
        snapshot = latest_snapshots.get(instrument.id)
        if snapshot:
            current_turnover += max(0.0, snapshot.value or 0.0)
            if snapshot.close_price > snapshot.yesterday_price:
                advancers += 1
            elif snapshot.close_price < snapshot.yesterday_price:
                decliners += 1
        bars = (
            trusted_eod_query(db, instrument.id)
            .order_by(EODBar.trading_date.desc()).limit(20).all()
        )
        if len(bars) >= 5 and bars[4].close > 0:
            returns_5d.append((bars[0].close / bars[4].close) - 1.0)
        if len(bars) >= 20:
            eligible_ema += 1
            ema = bars[-1].close
            alpha = 2.0 / 21.0
            for bar in reversed(bars[:-1]):
                ema = (bar.close * alpha) + (ema * (1.0 - alpha))
            current = snapshot.close_price if snapshot else bars[0].close
            above_ema20 += int(current > ema)
        for bar in bars:
            daily_turnover[bar.trading_date] = daily_turnover.get(bar.trading_date, 0.0) + max(0.0, bar.value or 0.0)

    if advancers + decliners == 0 or eligible_ema == 0:
        return None
    historical_turnovers = [value for _, value in sorted(daily_turnover.items(), reverse=True)[:20] if value > 0]
    if not historical_turnovers or not returns_5d:
        return None
    return classify_market_regime(
        advancers=advancers,
        decliners=decliners,
        stocks_above_ema20_pct=(above_ema20 / eligible_ema) * 100.0,
        current_turnover=current_turnover,
        median_turnover_20d=median(historical_turnovers),
        index_ret_5d=median(returns_5d),
    )
