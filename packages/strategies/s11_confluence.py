"""S11 — Multi-Indicator Confluence Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S11_MultiIndicatorConfluence(BaseStrategy):
    key = "multi_indicator_confluence"
    name_fa = "تأیید چندگانه اندیکاتوری"
    version = "1.0.0"
    required_features = {
        "ema_trend_score", "rsi_14", "macd_hist", "supertrend_direction", 
        "mfi_14", "obv_slope_20d", "real_buyer_power_ratio", "ichimoku_above_cloud",
        "close", "atr_14"
    }

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        close = f.get("close", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)
        
        count = 0
        if f.get("ema_trend_score", 0.0) >= 0.75:
            count += 1
        rsi = f.get("rsi_14", 50.0)
        if rsi > 50 and rsi < 70:
            count += 1
        if f.get("macd_hist", 0.0) > 0:
            count += 1
        if f.get("supertrend_direction", 0.0) == 1.0:
            count += 1
        if f.get("mfi_14", 50.0) > 50:
            count += 1
        if f.get("obv_slope_20d", 0.0) > 0:
            count += 1
        if f.get("real_buyer_power_ratio", 1.0) > 1.2:
            count += 1
        if f.get("ichimoku_above_cloud", 0.0) == 1.0:
            count += 1

        if count >= 5:
            vote = min(1.0, 0.4 + count * 0.08)
            entry_low = round(close * 0.99)
            entry_high = round(close * 1.01)
            max_chase = round(close * 1.02)
            stop_price = round(close - (1.5 * atr_14))
            targets = [round(close + (2.5 * atr_14)), round(close + (4.0 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=round(vote, 2),
                raw_score=float(count),
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=6,
                reason_fa=f"{count} اندیکاتور از ۸ اندیکاتور مستقل هم‌جهت هستند",
                risk_flags_fa=[],
            )
        return None
