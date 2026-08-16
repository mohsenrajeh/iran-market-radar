"""System settings and Central Risk Policy inspection routes."""
from fastapi import APIRouter
from packages.domain.risk_policy import ACTIVE_RISK_POLICY
from packages.market_rules.fees import TSE_EQUITY_FEES, EQUITY_ETF_FEES
from packages.shared.config import settings

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
def get_system_settings():
    """Returns the single source of truth for Risk Policy, Market Rules, and Fees."""
    policy_dict = ACTIVE_RISK_POLICY.to_dict()
    return {
        "trading_mode": "paper",
        "live_trading_enabled": False,
        "risk_kill_switch_armed": True,
        "risk_policy": policy_dict,
        "market_rules": {
            "tse_equity_fees": {
                "buy_fee_pct": float(TSE_EQUITY_FEES.buy_fee_rate) * 100,
                "sell_fee_pct": float(TSE_EQUITY_FEES.sell_fee_rate) * 100,
                "sell_tax_pct": float(TSE_EQUITY_FEES.sell_tax_rate) * 100,
                "round_trip_pct": round(float(TSE_EQUITY_FEES.round_trip_rate) * 100, 4),
            },
            "etf_fees": {
                "buy_fee_pct": float(EQUITY_ETF_FEES.buy_fee_rate) * 100,
                "sell_fee_pct": float(EQUITY_ETF_FEES.sell_fee_rate) * 100,
                "round_trip_pct": round(float(EQUITY_ETF_FEES.round_trip_rate) * 100, 4),
            },
            "price_limits": {
                "standard_tse_pct": 5.0,
                "base_volume_enabled": True,
            },
        },
        "risk_parameters": {
            "policy_version": ACTIVE_RISK_POLICY.version,
            "risk_per_trade_pct_nav": ACTIVE_RISK_POLICY.regimes["RISK_ON"].risk_per_trade_pct,
            "max_position_pct_nav": ACTIVE_RISK_POLICY.portfolio_limits.normal_max_position_weight_pct,
            "max_sector_pct_nav": ACTIVE_RISK_POLICY.portfolio_limits.sector_exposure_cap_pct,
            "max_open_positions": ACTIVE_RISK_POLICY.portfolio_limits.max_active_positions,
            "max_drawdown_kill_switch_pct": ACTIVE_RISK_POLICY.drawdown_ladder.dd_kill_switch_pct,
        },
    }
