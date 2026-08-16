"""Institutional Multi-Constraint Position Sizing Solver and Pre-Trade Risk Ticket Generator."""
from decimal import Decimal
from typing import TypedDict, Any, List, Dict
from packages.domain.risk_policy import ACTIVE_RISK_POLICY, RiskPolicy
from packages.domain.models import Portfolio, Position, PublishedSignal
from packages.market_rules.fees import TSE_EQUITY_FEES
from packages.shared.money import MoneyIRR


class PreTradeRiskTicket(TypedDict):
    symbol: str
    decision: str  # APPROVED, BLOCKED, WAIT_CHASE, BLOCKED_RISK, BLOCKED_SECTOR, BLOCKED_LIQUIDITY
    decision_reason_fa: str
    current_price: float
    planned_entry: float
    stop_price: float
    target1_price: float
    target2_price: float
    gross_reward_risk_ratio: float
    net_reward_risk_ratio: float
    current_r: float
    chase_status: str
    
    # Capital & Sizing
    portfolio_nav_rials: float
    risk_budget_rials: float
    risk_pct_nav: float
    effective_loss_pct: float
    
    # Sizing Breakdown
    recommended_position_rials: float
    recommended_quantity: int
    recommended_weight_pct: float
    
    # Stages (40% / 35% / 25%)
    stage1_quantity: int
    stage1_amount_rials: float
    stage2_quantity: int
    stage2_amount_rials: float
    stage3_quantity: int
    stage3_amount_rials: float
    
    # Execution Costs
    estimated_fees_rials: float
    estimated_tax_rials: float
    estimated_slippage_rials: float
    total_execution_cost_rials: float
    
    # Portfolio Impact Post-Trade
    cash_after_trade_rials: float
    cash_pct_after_trade: float
    gross_exposure_after_trade_pct: float
    sector_exposure_after_trade_pct: float
    cluster_exposure_after_trade_pct: float
    total_open_risk_after_trade_pct: float
    daily_new_risk_after_trade_pct: float
    
    # Policy Metadata
    policy_version: str
    regime: str
    is_kill_switch_active: bool


class PositionSizingSolver:
    """Mathematical multi-constraint position sizing solver."""

    def __init__(self, policy: RiskPolicy = ACTIVE_RISK_POLICY):
        self.policy = policy

    def solve(
        self,
        portfolio: Portfolio,
        signal: PublishedSignal,
        current_market_price: float,
        adtv_20d_rials: float = 50_000_000_000.0,
        sector_name: str | None = None,
        strategy_family: str = "technical_swing",
        rolling_correlations: Dict[str, float] | None = None,
        daily_already_allocated_risk_pct: float = 0.0,
        daily_already_allocated_notional_rials: float = 0.0,
        hwm_nav_rials: float | None = None,
    ) -> PreTradeRiskTicket:
        """
        Solves the complete multi-constraint position sizing optimization problem
        and generates an institutional Pre-Trade Risk Ticket.
        """
        open_positions = [p for p in portfolio.positions if p.is_open]
        total_pos_value = sum(p.quantity * p.current_price for p in open_positions)
        nav_rials = portfolio.cash + total_pos_value

        # Determine Market Regime
        regime_key = (signal.regime or "risk_on").upper()
        if regime_key not in self.policy.regimes:
            regime_key = "RISK_ON"
        regime_cfg = self.policy.regimes[regime_key]

        # Check Drawdown Ladder
        hwm = max(nav_rials, hwm_nav_rials or nav_rials, portfolio.initial_cash)
        drawdown_pct = ((hwm - nav_rials) / hwm * 100.0) if hwm > 0 else 0.0

        risk_trade_pct = regime_cfg.risk_per_trade_pct
        max_gross_exposure_pct = regime_cfg.max_gross_exposure_pct
        is_hard_kill = portfolio.kill_switch_active

        # Apply drawdown ladder reductions
        if drawdown_pct >= self.policy.drawdown_ladder.dd_kill_switch_pct:
            is_hard_kill = True
            risk_trade_pct = 0.0
            max_gross_exposure_pct = 0.0
        elif drawdown_pct >= self.policy.drawdown_ladder.dd_defensive_pct:
            risk_trade_pct = 0.0  # No new buys
            max_gross_exposure_pct = min(max_gross_exposure_pct, 20.0)
        elif drawdown_pct >= self.policy.drawdown_ladder.dd_moderate_pct:
            risk_trade_pct *= 0.50
            max_gross_exposure_pct = min(max_gross_exposure_pct, 35.0)
        elif drawdown_pct >= self.policy.drawdown_ladder.dd_warning_pct:
            risk_trade_pct *= 0.75

        # 1. Prices and Distance
        entry_price = signal.entry_zone.get("low", current_market_price) if signal.entry_zone else current_market_price
        stop_price = signal.invalidation.get("price", entry_price * 0.95) if signal.invalidation else entry_price * 0.95
        target1_price = signal.exit_plan.get("targets", [entry_price * 1.075])[0] if signal.exit_plan else entry_price * 1.075
        target2_price = signal.exit_plan.get("targets", [entry_price * 1.075, entry_price * 1.145])[1] if signal.exit_plan and len(signal.exit_plan.get("targets", [])) > 1 else target1_price * 1.065

        initial_risk_rials = max(1.0, entry_price - stop_price)
        stop_distance_pct = (initial_risk_rials / entry_price)

        # Chase status
        distance_from_entry_r = (current_market_price - entry_price) / initial_risk_rials
        chase_blocked = distance_from_entry_r > self.policy.staged_entry.max_chase_r

        # Costs: Round trip fee (1.2562%) + slippage (20 bps entry + exit = 0.40%) + gap buffer (0.50%)
        buy_fee = float(TSE_EQUITY_FEES.buy_fee_rate)
        sell_fee = float(TSE_EQUITY_FEES.sell_fee_rate) + float(TSE_EQUITY_FEES.sell_tax_rate)
        total_costs_pct = buy_fee + sell_fee + 0.0040 + 0.0050

        effective_loss_pct = stop_distance_pct + total_costs_pct

        # 2. Risk Budget
        risk_budget_rials = nav_rials * (risk_trade_pct / 100.0)
        risk_based_position_rials = risk_budget_rials / effective_loss_pct if effective_loss_pct > 0 else 0.0

        # 3. Multi-Constraint Capacity Solver
        # A. Symbol NAV Cap (Normal 8%, Exceptional 10% for highly liquid)
        max_sym_weight = self.policy.portfolio_limits.exceptional_max_position_weight_pct if adtv_20d_rials >= 500_000_000_000.0 else self.policy.portfolio_limits.normal_max_position_weight_pct
        cap_symbol_rials = nav_rials * (max_sym_weight / 100.0)

        # B. Sector Cap (18% NAV)
        sec_current_exposure = sum(p.quantity * p.current_price for p in open_positions if getattr(p, "sector", None) == sector_name)
        sec_remaining_rials = max(0.0, (nav_rials * (self.policy.portfolio_limits.sector_exposure_cap_pct / 100.0)) - sec_current_exposure)

        # C. Correlation Haircut
        corr_multiplier = 1.0
        if rolling_correlations:
            max_corr = max(rolling_correlations.values()) if rolling_correlations else 0.0
            if max_corr >= self.policy.portfolio_limits.correlation_haircut_threshold:
                corr_multiplier = self.policy.portfolio_limits.correlation_size_multiplier

        # D. Liquidity Capacity (Max 5% 20d ADTV)
        cap_liquidity_rials = adtv_20d_rials * (self.policy.portfolio_limits.max_adtv_20d_participation_pct / 100.0)

        # E. Cash Floor Capacity
        min_cash_reserve = nav_rials * (regime_cfg.min_cash_reserve_pct / 100.0)
        available_cash = max(0.0, portfolio.cash - min_cash_reserve)

        # F. Gross Portfolio Capacity
        current_gross_exposure = total_pos_value
        max_allowable_gross = nav_rials * (max_gross_exposure_pct / 100.0)
        portfolio_exposure_remaining = max(0.0, max_allowable_gross - current_gross_exposure)

        # G. Daily Exposure Capacity (Max 15% new per day)
        daily_exposure_remaining = max(0.0, (nav_rials * (self.policy.portfolio_limits.max_new_notional_exposure_per_day_pct / 100.0)) - daily_already_allocated_notional_rials)

        # Final Position in Rials
        final_position_rials = min(
            risk_based_position_rials * corr_multiplier,
            cap_symbol_rials,
            sec_remaining_rials,
            cap_liquidity_rials,
            available_cash / (1.0 + buy_fee),
            portfolio_exposure_remaining,
            daily_exposure_remaining,
        )

        final_quantity = int(final_position_rials / current_market_price) if current_market_price > 0 else 0
        recommended_position_rials = final_quantity * current_market_price
        recommended_weight_pct = (recommended_position_rials / nav_rials * 100.0) if nav_rials > 0 else 0.0

        # Stages: 40% / 35% / 25%
        s1_qty = int(final_quantity * 0.40)
        s2_qty = int(final_quantity * 0.35)
        s3_qty = int(final_quantity * 0.25)

        # Cost Calculations
        est_fees = recommended_position_rials * buy_fee
        est_tax = 0.0  # Buy has 0 tax
        est_slippage = recommended_position_rials * 0.0020
        total_costs = est_fees + est_tax + est_slippage

        # Simulated Post-Trade Metrics
        cash_after = portfolio.cash - (recommended_position_rials + est_fees)
        cash_pct_after = (cash_after / nav_rials * 100.0) if nav_rials > 0 else 0.0
        gross_exp_after = ((current_gross_exposure + recommended_position_rials) / nav_rials * 100.0) if nav_rials > 0 else 0.0
        sec_exp_after = ((sec_current_exposure + recommended_position_rials) / nav_rials * 100.0) if nav_rials > 0 else 0.0
        open_risk_after = sum((p.average_entry_price - (p.stop_loss or p.average_entry_price * 0.95)) * p.quantity for p in open_positions)
        open_risk_after_pct = ((open_risk_after + (initial_risk_rials * final_quantity)) / nav_rials * 100.0) if nav_rials > 0 else 0.0
        daily_new_risk_after_pct = daily_already_allocated_risk_pct + ((initial_risk_rials * final_quantity) / nav_rials * 100.0)

        # Decision Logic
        reasons_fa = []
        decision = "APPROVED"

        if is_hard_kill:
            decision = "BLOCKED"
            reasons_fa.append("کلید قطع اضطراری معامله (Kill Switch) فعال است.")
        elif len(open_positions) >= self.policy.portfolio_limits.max_active_positions:
            decision = "BLOCKED"
            reasons_fa.append(f"سقف تعداد معاملات همزمان ({self.policy.portfolio_limits.max_active_positions} پوزیشن) تکمیل است.")
        elif chase_blocked:
            decision = "WAIT_CHASE"
            reasons_fa.append(f"قیمت بیش از ۰.۳۵R ({distance_from_entry_r:+.2f}R) از نقطه ورود فرار کرده است.")
        elif final_quantity <= 0 or available_cash < 50_000_000:
            decision = "BLOCKED"
            reasons_fa.append("نقدینگی در دسترس با رعایت کف ۳۰٪ کفایت نمی‌کند.")
        elif open_risk_after_pct > self.policy.portfolio_limits.max_total_open_risk_pct:
            decision = "BLOCKED_RISK"
            reasons_fa.append(f"ریسک باز کل سبد ({open_risk_after_pct:.2f}٪) از سقف مجاز ۲.۵٪ عبور می‌کند.")
        elif sec_exp_after > self.policy.portfolio_limits.sector_exposure_cap_pct:
            decision = "BLOCKED_SECTOR"
            reasons_fa.append(f"تمرکز در صنعت ({sec_exp_after:.1f}٪) از سقف مجاز ۱۸٪ فراتر می‌رود.")
        else:
            reasons_fa.append("تمام گیت‌های مدیریت ریسک، نقدینگی و ظرفیت سبد پاس شدند.")

        target1_reward = max(0.0, target1_price - entry_price)
        gross_rr = round(target1_reward / initial_risk_rials, 2)
        net_rr = round(max(0.0, target1_reward - (entry_price * (buy_fee + sell_fee + 0.0040))) / (initial_risk_rials + (entry_price * (buy_fee + sell_fee + 0.0040))), 2)

        return {
            "symbol": signal.symbol,
            "decision": decision,
            "decision_reason_fa": " | ".join(reasons_fa),
            "current_price": current_market_price,
            "planned_entry": entry_price,
            "stop_price": stop_price,
            "target1_price": target1_price,
            "target2_price": target2_price,
            "gross_reward_risk_ratio": gross_rr,
            "net_reward_risk_ratio": net_rr,
            "current_r": round(distance_from_entry_r, 2),
            "chase_status": "CHASE_BLOCKED" if chase_blocked else "NORMAL_ENTRY",
            "portfolio_nav_rials": nav_rials,
            "risk_budget_rials": risk_budget_rials,
            "risk_pct_nav": risk_trade_pct,
            "effective_loss_pct": round(effective_loss_pct * 100.0, 2),
            "recommended_position_rials": recommended_position_rials,
            "recommended_quantity": final_quantity,
            "recommended_weight_pct": round(recommended_weight_pct, 2),
            "stage1_quantity": s1_qty,
            "stage1_amount_rials": s1_qty * current_market_price,
            "stage2_quantity": s2_qty,
            "stage2_amount_rials": s2_qty * current_market_price,
            "stage3_quantity": s3_qty,
            "stage3_amount_rials": s3_qty * current_market_price,
            "estimated_fees_rials": est_fees,
            "estimated_tax_rials": est_tax,
            "estimated_slippage_rials": est_slippage,
            "total_execution_cost_rials": total_costs,
            "cash_after_trade_rials": cash_after,
            "cash_pct_after_trade": round(cash_pct_after, 2),
            "gross_exposure_after_trade_pct": round(gross_exp_after, 2),
            "sector_exposure_after_trade_pct": round(sec_exp_after, 2),
            "cluster_exposure_after_trade_pct": round(sec_exp_after, 2),
            "total_open_risk_after_trade_pct": round(open_risk_after_pct, 2),
            "daily_new_risk_after_trade_pct": round(daily_new_risk_after_pct, 2),
            "policy_version": self.policy.version,
            "regime": regime_key,
            "is_kill_switch_active": is_hard_kill,
        }


position_sizing_solver = PositionSizingSolver()
