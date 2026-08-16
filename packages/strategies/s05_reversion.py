"""S05 — Short-Term Mean Reversion Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S05_SelectiveMeanReversion(BaseStrategy):
    key = "selective_mean_reversion"
    name_fa = "بازگشت میانگین انتخابی از اشباع فروش"
    version = "1.0.0"
    required_features = {"ret_5d", "channel_pos_20d", "close", "atr_14"}

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        ret_5d = f.get("ret_5d", 0.0)
        channel_pos = f.get("channel_pos_20d", 0.5)
        close = f.get("close", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)

        # Do not buy during broad distribution/bear market unless strong quality filter
        if ctx.market_regime == "risk_off":
            return None

        # Extreme 5-day drop (< -7%) and at the floor of 20-day channel (< 0.10)
        if ret_5d < -0.06 and channel_pos <= 0.10:
            entry_low = round(close * 0.99)
            entry_high = round(close * 1.01)
            max_chase = round(close * 1.015)
            stop_price = round(close - (1.0 * atr_14))
            targets = [round(close + (1.5 * atr_14)), round(close + (2.5 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=0.64,
                raw_score=round(abs(ret_5d) * 100, 1),
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=3,
                reason_fa=f"افت قیمتی شدید ۵ روزه ({ret_5d * 100:.1f}٪) و حضور در کف کانال نوسان (پتانسیل بازگشت سریع)",
                risk_flags_fa=["ریسک صف فروش در صورت ادامه فشار عرضه"],
            )
        return None
