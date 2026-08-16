"""S04 — Trend Pullback / Continuation Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S04_TrendPullback(BaseStrategy):
    key = "trend_pullback"
    name_fa = "پولبک به سطوح حمایتی در روند صعودی"
    version = "1.0.0"
    required_features = {"ret_60d", "ema_20", "close", "ret_3d", "atr_14"}

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        ret_60d = f.get("ret_60d", 0.0)
        close = f.get("close", 0.0)
        ema_20 = f.get("ema_20", close)
        ret_3d = f.get("ret_3d", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)

        # Long-term uptrend (60d > 10%), short-term pullback (3d between -1.5% and -5%), price resting near EMA 20
        if ret_60d > 0.08 and -0.05 <= ret_3d <= -0.01:
            dist_to_ema20 = abs(close - ema_20) / close
            if dist_to_ema20 <= 0.025:  # Within 2.5% of EMA 20
                entry_low = round(close * 0.99)
                entry_high = round(close * 1.01)
                max_chase = round(close * 1.02)
                stop_price = round(ema_20 - (1.3 * atr_14))
                targets = [round(close + (2.0 * atr_14)), round(close + (3.2 * atr_14))]

                return CandidateResult(
                    strategy_key=self.key,
                    vote=0.72,
                    raw_score=75.0,
                    entry_low=entry_low,
                    entry_high=entry_high,
                    max_chase=max_chase,
                    stop_price=stop_price,
                    target_prices=targets,
                    time_stop_sessions=6,
                    reason_fa="پولبک کنترل‌شده به میانگین متحرک ۲۰ روزه در ساختار روند صعودی",
                    risk_flags_fa=[],
                )
        return None
