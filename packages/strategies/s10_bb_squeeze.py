"""S10 — Bollinger Bands Squeeze Breakout Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S10_BBSqueezeBreakout(BaseStrategy):
    key = "bb_squeeze_breakout"
    name_fa = "فشردگی بولینگر — انفجار نوسان"
    version = "1.0.0"
    required_features = {"bb_squeeze", "vol_z_score_20d", "supertrend_direction", "close", "atr_14"}

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        bb_squeeze = f.get("bb_squeeze", 0.0)
        vol_z_score_20d = f.get("vol_z_score_20d", 0.0)
        supertrend_direction = f.get("supertrend_direction", 0.0)
        close = f.get("close", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)

        if bb_squeeze == 1.0 and vol_z_score_20d > 1.5 and supertrend_direction == 1.0:
            vote = min(1.0, 0.55 + vol_z_score_20d * 0.1)
            entry_low = round(close * 0.99)
            entry_high = round(close * 1.015)
            max_chase = round(close * 1.025)
            stop_price = round(close - (1.5 * atr_14))
            targets = [round(close + (3.0 * atr_14)), round(close + (5.0 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=round(vote, 2),
                raw_score=round(vol_z_score_20d, 1),
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=5,
                reason_fa=f"فشردگی بولینگر و انفجار حجم در جهت روند (امتیاز حجم: {vol_z_score_20d:.1f})",
                risk_flags_fa=[],
            )
        return None
