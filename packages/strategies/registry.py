"""Strategy Registry for registering and running alpha hypotheses."""
from packages.strategies.base import BaseStrategy, StrategyContext, CandidateResult
from packages.strategies.s01_momentum import S01_CrossSectionalMomentum
from packages.strategies.s02_trend import S02_TimeSeriesTrend
from packages.strategies.s03_breakout import S03_BreakoutVolume
from packages.strategies.s04_pullback import S04_TrendPullback
from packages.strategies.s05_reversion import S05_SelectiveMeanReversion
from packages.strategies.s06_volume import S06_VolumeAnomaly
from packages.strategies.s07_client_flow import S07_ClientFlowAccumulation
from packages.strategies.s08_ichimoku import S08_IchimokuCloudTrend
from packages.strategies.s09_sector_rotation import S09_SectorRotation
from packages.strategies.s10_bb_squeeze import S10_BBSqueezeBreakout
from packages.strategies.s11_confluence import S11_MultiIndicatorConfluence
from packages.strategies.s12_smart_money_divergence import S12_SmartMoneyDivergence


class StrategyRegistry:
    """Central registry of all available quantitative strategies."""

    def __init__(self):
        self._strategies: dict[str, BaseStrategy] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(S01_CrossSectionalMomentum())
        self.register(S02_TimeSeriesTrend())
        self.register(S03_BreakoutVolume())
        self.register(S04_TrendPullback())
        self.register(S05_SelectiveMeanReversion())
        self.register(S06_VolumeAnomaly())
        self.register(S07_ClientFlowAccumulation())
        self.register(S08_IchimokuCloudTrend())
        self.register(S09_SectorRotation())
        self.register(S10_BBSqueezeBreakout())
        self.register(S11_MultiIndicatorConfluence())
        self.register(S12_SmartMoneyDivergence())

    def register(self, strategy: BaseStrategy):
        self._strategies[strategy.key] = strategy

    def get(self, key: str) -> BaseStrategy | None:
        return self._strategies.get(key)

    def list_strategies(self) -> list[BaseStrategy]:
        return list(self._strategies.values())

    def evaluate_all(self, ctx: StrategyContext) -> list[CandidateResult]:
        """Runs all eligible strategies against the context."""
        candidates = []
        for strat in self._strategies.values():
            if ctx.horizon in strat.supported_horizons:
                res = strat.evaluate(ctx)
                if res is not None:
                    res.family = STRATEGY_FAMILY_BY_KEY.get(strat.key, "unclassified")
                    candidates.append(res)
        return candidates


# Singleton instance
strategy_registry = StrategyRegistry()


STRATEGY_FAMILY_BY_KEY = {
    "cross_sectional_momentum": "trend",
    "time_series_trend": "trend",
    "trend_pullback": "trend",
    "ichimoku_cloud_trend": "trend",
    "breakout_volume": "breakout_volatility",
    "volume_anomaly": "breakout_volatility",
    "bb_squeeze_breakout": "breakout_volatility",
    "selective_mean_reversion": "mean_reversion",
    "client_flow": "smart_money",
    "smart_money_divergence": "smart_money",
    "sector_rotation": "relative_strength",
    # Composite signals are useful evidence but are not counted as an independent family.
    "multi_indicator_confluence": "composite",
}
