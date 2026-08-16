"""Quantitative Trading Metrics, R-Multiple Engine, and Chase Prevention."""
from decimal import Decimal
from typing import TypedDict, Literal
from packages.market_rules.fees import TSE_EQUITY_FEES, calculate_trade_fees

EntryState = Literal[
    "READY",
    "WAIT_FOR_ENTRY",
    "WAIT_FOR_RETEST",
    "CHASE_BLOCKED",
    "QUEUE_BLOCKED",
    "LIQUIDITY_BLOCKED",
    "RISK_BLOCKED",
    "REGIME_BLOCKED",
    "DATA_BLOCKED",
]


class RMultipleMetrics(TypedDict):
    initial_risk_rials: float
    initial_risk_pct: float
    current_price: float
    planned_entry: float
    stop_price: float
    target1_price: float
    target2_price: float
    target1_pct: float
    target2_pct: float
    stop_pct: float
    gross_reward_risk_ratio: float
    net_reward_risk_ratio: float
    current_r: float
    distance_from_entry_r: float
    entry_state: EntryState
    entry_state_reason_fa: str
    stage1_pct: float
    stage2_pct: float
    stage3_pct: float


def compute_r_multiples(
    current_price: float,
    planned_entry: float,
    stop_price: float,
    target1_price: float | None = None,
    target2_price: float | None = None,
    slippage_bps: float = 20.0,
    regime: str = "risk_on",
    data_fresh: bool = True,
    is_queue_locked: bool = False,
    liquidity_score: float = 80.0,
) -> RMultipleMetrics:
    """
    Computes all trade metrics and R-multiples strictly at runtime from price levels.
    Guarantees no hardcoded or contradictory R/R or percentage strings.
    """
    # Guard against invalid inputs
    if planned_entry <= 0:
        planned_entry = current_price
    if stop_price <= 0 or stop_price >= planned_entry:
        stop_price = planned_entry * 0.95

    # Defaults for targets if not provided
    if not target1_price or target1_price <= planned_entry:
        target1_price = planned_entry * 1.075
    if not target2_price or target2_price <= target1_price:
        target2_price = planned_entry * 1.145

    # 1. Initial Risk (1R)
    initial_risk_rials = max(1.0, planned_entry - stop_price)
    initial_risk_pct = (initial_risk_rials / planned_entry) * 100.0

    # 2. Percentage movements from planned entry
    target1_pct = ((target1_price - planned_entry) / planned_entry) * 100.0
    target2_pct = ((target2_price - planned_entry) / planned_entry) * 100.0
    stop_pct = -((planned_entry - stop_price) / planned_entry) * 100.0

    # 3. Gross Reward to Risk Ratio
    target1_reward = max(0.0, target1_price - planned_entry)
    gross_rr = round(target1_reward / initial_risk_rials, 2)

    # 4. Net Reward to Risk Ratio (Accounting for 1.2562% fees + slippage)
    buy_fees = float(TSE_EQUITY_FEES.buy_fee_rate)
    sell_fees = float(TSE_EQUITY_FEES.sell_fee_rate) + float(TSE_EQUITY_FEES.sell_tax_rate)
    round_trip_fee_rate = buy_fees + sell_fees
    slippage_rate = (slippage_bps / 10_000.0) * 2.0  # Entry + Exit slippage

    total_cost_per_share = planned_entry * (round_trip_fee_rate + slippage_rate)
    effective_loss_rials = initial_risk_rials + total_cost_per_share
    effective_gain_rials = max(0.0, target1_reward - total_cost_per_share)
    net_rr = round(effective_gain_rials / effective_loss_rials, 2) if effective_loss_rials > 0 else 0.0

    # 5. Current Position in R-multiples
    current_r = round((current_price - planned_entry) / initial_risk_rials, 2)
    distance_from_entry_r = round((current_price - planned_entry) / initial_risk_rials, 2)

    # 6. Entry State Machine & Chase Prevention
    entry_state: EntryState = "READY"
    entry_state_reason_fa = "قیمت در محدوده ورود بهینه قرار دارد."

    if not data_fresh:
        entry_state = "DATA_BLOCKED"
        entry_state_reason_fa = "داده‌های بازار یا صورت‌های مالی منقضی شده‌اند."
    elif regime == "halted":
        entry_state = "REGIME_BLOCKED"
        entry_state_reason_fa = "بازار در وضعیت تعلیق یا توقف کلی (Halted) است."
    elif is_queue_locked:
        entry_state = "QUEUE_BLOCKED"
        entry_state_reason_fa = "صف سنگین خرید بدون عرضه، ورود را پرریسک کرده است."
    elif liquidity_score < 60.0:
        entry_state = "LIQUIDITY_BLOCKED"
        entry_state_reason_fa = "نقدشوندگی سهم کمتر از حد نصاب سامانه است."
    elif distance_from_entry_r > 0.35:
        entry_state = "CHASE_BLOCKED"
        entry_state_reason_fa = f"قیمت بیش از ۰.۳۵R ({distance_from_entry_r:+.2f}R) از نقطه ورود فرار کرده است؛ تعقیب قیمت ممنوع است."
    elif current_price < planned_entry * 0.985:
        entry_state = "WAIT_FOR_RETEST"
        entry_state_reason_fa = "قیمت پایین‌تر از محدوده ورود است؛ در انتظار تأیید بازگشت و پولبک."
    elif current_price > planned_entry * 1.015:
        entry_state = "WAIT_FOR_ENTRY"
        entry_state_reason_fa = "در انتظار رسیدن قیمت به سطح ورود برنامه‌ریزی‌شده."

    return {
        "initial_risk_rials": initial_risk_rials,
        "initial_risk_pct": round(initial_risk_pct, 2),
        "current_price": current_price,
        "planned_entry": planned_entry,
        "stop_price": stop_price,
        "target1_price": target1_price,
        "target2_price": target2_price,
        "target1_pct": round(target1_pct, 2),
        "target2_pct": round(target2_pct, 2),
        "stop_pct": round(stop_pct, 2),
        "gross_reward_risk_ratio": gross_rr,
        "net_reward_risk_ratio": net_rr,
        "current_r": current_r,
        "distance_from_entry_r": distance_from_entry_r,
        "entry_state": entry_state,
        "entry_state_reason_fa": entry_state_reason_fa,
        "stage1_pct": 40.0,
        "stage2_pct": 35.0,
        "stage3_pct": 25.0,
    }
