"""Base strategy protocol and candidate evaluation structures."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategyContext:
    symbol: str
    instrument_id: str
    name_fa: str
    market: str
    sector_name: str | None
    horizon: str
    features: dict[str, float]
    market_regime: str
    allowed_min: float
    allowed_max: float
    fundamental: dict[str, float] = field(default_factory=dict)


@dataclass
class CandidateResult:
    strategy_key: str
    vote: float                     # 0.0 to 1.0 signal strength / confidence
    raw_score: float                # Raw alpha score
    entry_low: float
    entry_high: float
    max_chase: float
    stop_price: float
    target_prices: list[float]
    time_stop_sessions: int
    reason_fa: str
    risk_flags_fa: list[str]
    family: str = "unclassified"


class BaseStrategy(ABC):
    """Abstract Strategy interface."""

    key: str = "base_strategy"
    name_fa: str = "استراتژی پایه"
    version: str = "1.0.0"
    required_features: set[str] = set()
    supported_horizons: set[str] = {"3d", "5d", "10d"}

    @abstractmethod
    def evaluate(self, ctx: StrategyContext) -> CandidateResult | None:
        """Evaluates features and produces a trading candidate if eligible."""
        pass
