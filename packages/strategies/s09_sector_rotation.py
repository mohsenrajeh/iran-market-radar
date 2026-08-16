"""S09 — Sector Rotation Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S09_SectorRotation(BaseStrategy):
    key = "sector_rotation"
    name_fa = "چرخش نقدینگی و پیشتازی صنعت"
    version = "1.0.0"
    required_features = {"ret_20d", "close", "atr_14"}

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        ret_20d = f.get("ret_20d", 0.0)
        close = f.get("close", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)

        # In strong industries (top sectors)
        if ctx.sector_name in ("فلزات اساسی", "محصولات شیمیایی", "استخراج کانه‌های فلزی") and ret_20d > 0.05:
            entry_low = round(close * 0.99)
            entry_high = round(close * 1.015)
            max_chase = round(close * 1.025)
            stop_price = round(close - (1.5 * atr_14))
            targets = [round(close + (2.0 * atr_14)), round(close + (3.5 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=0.74,
                raw_score=78.0,
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=7,
                reason_fa=f"پیشتازی صنعت {ctx.sector_name} در جذب سرمایه و بازده ۲۰ روزه مثبت سهم",
                risk_flags_fa=[],
            )
        return None
