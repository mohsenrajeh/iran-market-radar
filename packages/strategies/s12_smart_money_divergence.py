"""S12 — Smart Money Divergence Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S12_SmartMoneyDivergence(BaseStrategy):
    key = "smart_money_divergence"
    name_fa = "واگرایی پول هوشمند"
    version = "1.0.0"
    required_features = {
        "ret_5d", "mfi_14", "obv_slope_20d", "real_buyer_power_ratio", 
        "channel_pos_20d", "close", "atr_14"
    }

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        ret_5d = f.get("ret_5d", 0.0)
        mfi_14 = f.get("mfi_14", 50.0)
        obv_slope_20d = f.get("obv_slope_20d", 0.0)
        real_buyer_power_ratio = f.get("real_buyer_power_ratio", 1.0)
        channel_pos_20d = f.get("channel_pos_20d", 0.5)
        close = f.get("close", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)

        if (ret_5d < -0.03 and mfi_14 > 45 and obv_slope_20d > 0 and 
            real_buyer_power_ratio > 1.3 and channel_pos_20d < 0.3):
            
            vote = min(1.0, 0.5 + real_buyer_power_ratio * 0.15)
            entry_low = round(close * 0.99)
            entry_high = round(close * 1.01)
            max_chase = round(close * 1.02)
            stop_price = round(close - (2.0 * atr_14))
            targets = [round(close + (2.0 * atr_14)), round(close + (4.0 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=round(vote, 2),
                raw_score=round(real_buyer_power_ratio, 2),
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=10,
                reason_fa=f"افت قیمت اما انباشت پول هوشمند (واگرایی مثبت، قدرت خریدار: {real_buyer_power_ratio:.1f})",
                risk_flags_fa=[],
            )
        return None
