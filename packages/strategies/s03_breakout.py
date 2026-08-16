"""S03 — Breakout + Volume Expansion Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S03_BreakoutVolume(BaseStrategy):
    key = "breakout_volume"
    name_fa = "شکست سقف با افزایش حجم"
    version = "1.0.0"
    required_features = {"dist_to_20_high", "vol_z_score_20d", "close", "atr_14"}

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        dist_high = f.get("dist_to_20_high", -1.0)
        vol_z = f.get("vol_z_score_20d", 0.0)
        close = f.get("close", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)

        # Price within 0.5% of 20-day high (or breaking above) + robust volume z-score >= 1.5
        if dist_high >= -0.008 and vol_z >= 1.4:
            vote = min(1.0, 0.6 + (vol_z * 0.1))
            entry_low = round(close * 0.995)
            entry_high = round(close * 1.02)
            max_chase = round(close * 1.035)
            stop_price = round(close - (1.2 * atr_14))
            targets = [round(close + (2.2 * atr_14)), round(close + (4.0 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=round(vote, 2),
                raw_score=round(vol_z * 10, 1),
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=5,
                reason_fa=f"شکست سقف قیمتی ۲۰ روزه همراه با جهش حجم معاملات (زد-اسکور {vol_z:.1f})",
                risk_flags_fa=[],
            )
        return None
