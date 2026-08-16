"""Central Institutional Risk Policy for Iran Market Radar.
Single Source of Truth for all risk limits, position sizing, regime allocation, and kill switches.
"""
import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Literal, Dict, Any

RegimeType = Literal["RISK_ON", "NEUTRAL", "RISK_OFF", "HALTED"]


@dataclass(frozen=True)
class RegimeConfig:
    max_gross_exposure_pct: float
    min_cash_reserve_pct: float
    risk_per_trade_pct: float
    description_fa: str


@dataclass(frozen=True)
class StrategyFamilyAllocations:
    fundamental_trend_pct: float = 50.0
    technical_swing_pct: float = 30.0
    codal_event_driven_pct: float = 20.0


@dataclass(frozen=True)
class StrategyTierCaps:
    champion_max_pct: float = 85.0
    diversifier_max_pct: float = 10.0
    challenger_max_pct: float = 5.0


@dataclass(frozen=True)
class PortfolioRiskLimits:
    max_active_positions: int = 10
    normal_max_position_weight_pct: float = 8.0
    exceptional_max_position_weight_pct: float = 10.0
    sector_exposure_cap_pct: float = 18.0
    max_positions_per_sector: int = 3
    correlated_cluster_cap_pct: float = 20.0
    correlation_haircut_threshold: float = 0.70
    correlation_size_multiplier: float = 0.50
    max_total_open_risk_pct: float = 2.50
    max_new_risk_per_day_pct: float = 0.80
    max_new_notional_exposure_per_day_pct: float = 15.0
    max_adtv_20d_participation_pct: float = 5.0
    max_estimated_exit_days: int = 2


@dataclass(frozen=True)
class DrawdownLadder:
    dd_warning_pct: float = 4.0        # RiskPerTrade * 0.75
    dd_moderate_pct: float = 6.0       # RiskPerTrade * 0.50, Max Exposure = 35%
    dd_defensive_pct: float = 8.0      # No new buys, Target Exposure <= 20%
    dd_kill_switch_pct: float = 12.0   # HARD KILL SWITCH


@dataclass(frozen=True)
class DailyLossCircuitBreaker:
    daily_loss_step1_pct: float = 1.0  # Risk * 0.50
    daily_loss_step2_pct: float = 1.5  # Stop all new buys
    daily_loss_step3_pct: float = 2.0  # Cancel pending buys, risk reduction mode


@dataclass(frozen=True)
class StagedEntryConfig:
    stage1_pct: float = 40.0
    stage2_pct: float = 35.0
    stage3_pct: float = 25.0
    max_chase_r: float = 0.35
    allow_averaging_down: bool = False


@dataclass
class RiskPolicy:
    """Institutional Central Risk Policy Model."""
    policy_id: str = "POL-TSE-2026-V2.5"
    version: str = "2.5.0-ENTERPRISE"
    effective_at: str = "2026-08-16T00:00:00Z"
    created_at: str = "2026-08-16T00:00:00Z"
    approved_by: str = "Chief Risk Officer (CRO) & Quant Committee"
    status: str = "ACTIVE"
    
    # 1. Market Regimes
    regimes: Dict[str, RegimeConfig] = field(default_factory=lambda: {
        "RISK_ON": RegimeConfig(
            max_gross_exposure_pct=70.0,
            min_cash_reserve_pct=30.0,
            risk_per_trade_pct=0.35,
            description_fa="بازار صعودی و پرنقدینگی — تخصیص تا ۷۰٪ سهام و ۰.۳۵٪ ریسک به ازای هر معامله",
        ),
        "NEUTRAL": RegimeConfig(
            max_gross_exposure_pct=50.0,
            min_cash_reserve_pct=50.0,
            risk_per_trade_pct=0.25,
            description_fa="بازار متعادل و نوسانی — تخصیص ۵۰٪ سهام و ۰.۲۵٪ ریسک به ازای هر معامله",
        ),
        "RISK_OFF": RegimeConfig(
            max_gross_exposure_pct=25.0,
            min_cash_reserve_pct=75.0,
            risk_per_trade_pct=0.15,
            description_fa="بازار فرسایشی و منفی — حداقل ۷۵٪ نقدینگی امن و ۰.۱۵٪ ریسک در هر معامله",
        ),
        "HALTED": RegimeConfig(
            max_gross_exposure_pct=0.0,
            min_cash_reserve_pct=100.0,
            risk_per_trade_pct=0.0,
            description_fa="بازار متوقف یا بحرانی — توقف کامل خریدهای جدید",
        ),
    })

    # 2. Strategy Buckets & Caps
    strategy_families: StrategyFamilyAllocations = field(default_factory=StrategyFamilyAllocations)
    strategy_tiers: StrategyTierCaps = field(default_factory=StrategyTierCaps)

    # 3. Portfolio & Sizing Limits
    portfolio_limits: PortfolioRiskLimits = field(default_factory=PortfolioRiskLimits)
    drawdown_ladder: DrawdownLadder = field(default_factory=DrawdownLadder)
    daily_circuit_breaker: DailyLossCircuitBreaker = field(default_factory=DailyLossCircuitBreaker)
    staged_entry: StagedEntryConfig = field(default_factory=StagedEntryConfig)

    @property
    def tse_equity_roundtrip_fee_pct(self) -> float:
        return 1.2562

    def compute_config_hash(self) -> str:
        """Generates deterministic SHA-256 hash of all policy parameters."""
        data_str = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["config_hash"] = self.compute_config_hash()
        d["tse_equity_roundtrip_fee_pct"] = self.tse_equity_roundtrip_fee_pct
        return d


# Singleton Active Risk Policy Instance
ACTIVE_RISK_POLICY = RiskPolicy()
