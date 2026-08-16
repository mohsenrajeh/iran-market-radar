"""S02 — Time-Series Trend Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S02_TimeSeriesTrend(BaseStrategy):
    key = "time_series_trend"
    name_fa = "روند میان‌مدت و چینش میانگین‌ها"
    version = "1.0.0"
    required_features = {"ema_trend_score", "close", "ema_20", "atr_14"}

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        trend_score = f.get("ema_trend_score", 0.0)
        close = f.get("close", 0.0)
        ema_20 = f.get("ema_20", close)
        atr_14 = f.get("atr_14", close * 0.02)

        # Full alignment across EMA 10, 20, 50, 100
        if trend_score >= 0.75 and close > ema_20:
            vote = 0.80 if trend_score == 1.0 else 0.65
            entry_low = round(close * 0.99)
            entry_high = round(close * 1.01)
            max_chase = round(close * 1.025)
            stop_price = round(ema_20 - atr_14)
            targets = [round(close + (1.8 * atr_14)), round(close + (3.0 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=vote,
                raw_score=round(trend_score * 100, 1),
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=7,
                reason_fa="چینش صعودی کامل میانگین‌های متحرک و تثبیت قیمت بالای EMA 20",
                risk_flags_fa=[],
            )
        return None
