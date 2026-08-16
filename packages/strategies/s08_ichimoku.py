"""S08 — Ichimoku Cloud Trend Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S08_IchimokuCloudTrend(BaseStrategy):
    key = "ichimoku_cloud_trend"
    name_fa = "ایچیموکو — روند ابری"
    version = "1.0.0"
    required_features = {"ichimoku_above_cloud", "ichimoku_tenkan", "ichimoku_kijun", "adx_14", "ema_trend_score", "close", "atr_14"}

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        ichimoku_above_cloud = f.get("ichimoku_above_cloud", 0.0)
        ichimoku_tenkan = f.get("ichimoku_tenkan", 0.0)
        ichimoku_kijun = f.get("ichimoku_kijun", 0.0)
        adx_14 = f.get("adx_14", 0.0)
        ema_trend_score = f.get("ema_trend_score", 0.0)
        close = f.get("close", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)

        if ichimoku_above_cloud == 1.0 and ichimoku_tenkan > ichimoku_kijun and adx_14 > 25 and ema_trend_score >= 0.5:
            vote = min(1.0, 0.5 + (adx_14 - 25) * 0.01)
            entry_low = round(close * 0.995)
            entry_high = round(close * 1.02)
            max_chase = round(close * 1.03)
            stop_price = round(close - (2.0 * atr_14))
            targets = [round(close + (2.5 * atr_14)), round(close + (4.0 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=round(vote, 2),
                raw_score=round(adx_14, 1),
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=7,
                reason_fa=f"قیمت بالای ابر کومو، کراس تنکان و کیجون، روند قوی با ADX برابر {adx_14:.1f}",
                risk_flags_fa=[],
            )
        return None
