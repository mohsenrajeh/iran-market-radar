"""S07 — Real/Legal Client Flow Accumulation Strategy (حقیقی / حقوقی)."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S07_ClientFlowAccumulation(BaseStrategy):
    key = "client_flow"
    name_fa = "ورود پول هوشمند و قدرت خریدار حقیقی"
    version = "1.0.0"
    required_features = {"real_buyer_power_ratio", "net_real_inflow_pct", "close", "atr_14"}

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        buyer_power = f.get("real_buyer_power_ratio", 1.0)
        inflow_pct = f.get("net_real_inflow_pct", 0.0)
        streak = f.get("real_accumulation_streak", 0.0)
        close = f.get("close", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)

        # Buyer power >= 1.4x (سرانه خرید حقیقی > ۱.۴ برابر سرانه فروش) + positive net real inflow
        if buyer_power >= 1.35 and inflow_pct > 0.05:
            vote = min(1.0, 0.60 + (buyer_power * 0.1) + (streak * 0.05))
            entry_low = round(close * 0.99)
            entry_high = round(close * 1.015)
            max_chase = round(close * 1.025)
            stop_price = round(close - (1.4 * atr_14))
            targets = [round(close + (2.0 * atr_14)), round(close + (3.6 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=round(vote, 2),
                raw_score=round(buyer_power * 25, 1),
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=5,
                reason_fa=f"سرانه خرید حقیقی {buyer_power:.2f} برابر سرانه فروش و ورود پول مثبت ({inflow_pct * 100:.1f}٪)",
                risk_flags_fa=[],
            )
        return None
