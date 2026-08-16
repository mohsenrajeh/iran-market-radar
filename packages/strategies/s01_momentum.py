"""S01 — Cross-Sectional Momentum / Relative Strength Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S01_CrossSectionalMomentum(BaseStrategy):
    key = "cross_sectional_momentum"
    name_fa = "مومنتوم مقطعی و قدرت نسبی"
    version = "1.0.0"
    required_features = {"ret_20d", "ret_60d", "close", "atr_14"}

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        ret_20d = f.get("ret_20d", 0.0)
        ret_60d = f.get("ret_60d", 0.0)
        close = f.get("close", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)

        # Candidate criteria: strong 20-day and 60-day relative outperformance
        if ret_20d > 0.04 and ret_60d > 0.08:
            vote = min(1.0, 0.5 + (ret_20d * 2.0))
            entry_low = round(close * 0.995)
            entry_high = round(close * 1.015)
            max_chase = round(close * 1.03)
            stop_price = round(close - (1.5 * atr_14))
            targets = [round(close + (2.0 * atr_14)), round(close + (3.5 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=round(vote, 2),
                raw_score=round(ret_20d * 100, 1),
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=5,
                reason_fa=f"قدرت نسبی بالا و بازده ۲۰ روزه مثبت ({ret_20d * 100:.1f}٪)",
                risk_flags_fa=[],
            )
        return None
