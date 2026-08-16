"""S06 — Volume / Turnover Anomaly Strategy."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult


class S06_VolumeAnomaly(BaseStrategy):
    key = "volume_anomaly"
    name_fa = "حجم مشکوک و جهش ارزش معاملات"
    version = "1.0.0"
    required_features = {"volume_ratio_20d", "vol_z_score_20d", "close", "ret_1d", "atr_14"}

    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        f = ctx.features
        vol_ratio = f.get("volume_ratio_20d", 1.0)
        vol_z = f.get("vol_z_score_20d", 0.0)
        ret_1d = f.get("ret_1d", 0.0)
        close = f.get("close", 0.0)
        atr_14 = f.get("atr_14", close * 0.02)

        # Volume >= 2.0x 20-day mean, positive price action (> 0.5%)
        if vol_ratio >= 2.0 and vol_z >= 1.5 and ret_1d > 0.005:
            entry_low = round(close * 0.995)
            entry_high = round(close * 1.02)
            max_chase = round(close * 1.03)
            stop_price = round(close - (1.3 * atr_14))
            targets = [round(close + (2.0 * atr_14)), round(close + (3.8 * atr_14))]

            return CandidateResult(
                strategy_key=self.key,
                vote=round(min(1.0, 0.65 + (vol_ratio * 0.05)), 2),
                raw_score=round(vol_ratio * 20, 1),
                entry_low=entry_low,
                entry_high=entry_high,
                max_chase=max_chase,
                stop_price=stop_price,
                target_prices=targets,
                time_stop_sessions=5,
                reason_fa=f"حجم معاملات {vol_ratio:.1f} برابر میانگین ماهانه همراه با کندل مثبت",
                risk_flags_fa=[],
            )
        return None
