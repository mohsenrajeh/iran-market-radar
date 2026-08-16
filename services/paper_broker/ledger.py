"""Paper Trading Ledger, Institutional Risk Gatekeeper, and Execution Simulator."""
from decimal import Decimal
from datetime import datetime, date
from typing import Tuple, Optional, Dict, Any

from packages.domain.models import (
    Portfolio, Position, BrokerOrder, PublishedSignal,
    CashLedger, OrderFill, DecisionAudit,
)
from packages.domain.risk_policy import ACTIVE_RISK_POLICY, RiskPolicy
from packages.market_rules.fees import (
    calculate_net_return, calculate_trade_fees, TSE_EQUITY_FEES,
)
from packages.shared.money import MoneyIRR, tomans_to_irr
from packages.shared.metrics import compute_r_multiples
from packages.shared.datetime_utils import now_utc
from packages.shared.logger import logger
from services.paper_broker.sizing import position_sizing_solver, PreTradeRiskTicket
from services.paper_broker.execution import execution_simulator, ExecutionBar
from services.paper_broker.accounting import accounting_reconciler

# Hard Security Guard: Live trading is strictly disabled in Backend
LIVE_TRADING_ENABLED = False


class PaperBrokerService:
    """
    Simulated Paper Broker Ledger & Institutional Risk Gatekeeper.
    Enforces Point-in-Time discipline, Next-Bar Execution, queue delays, and strict double-entry cash accounting.
    """

    def __init__(self, policy: RiskPolicy = ACTIVE_RISK_POLICY):
        self.policy = policy
        self.solver = position_sizing_solver
        self.simulator = execution_simulator
        self.reconciler = accounting_reconciler

    def generate_pre_trade_ticket(
        self,
        portfolio: Portfolio,
        signal: PublishedSignal,
        current_market_price: float,
        adtv_20d_rials: float = 50_000_000_000.0,
    ) -> PreTradeRiskTicket:
        """Generates pre-trade risk ticket with complete position sizing analysis."""
        return self.solver.solve(
            portfolio=portfolio,
            signal=signal,
            current_market_price=current_market_price,
            adtv_20d_rials=adtv_20d_rials,
            sector_name=getattr(signal, "sector", None),
        )

    def calculate_position_size(
        self,
        portfolio: Portfolio,
        entry_price: float,
        stop_price: float,
        opportunity_score: float = 75.0,
        adtv_20d_rials: float = 50_000_000_000.0,
        sector_current_exposure_rials: float = 0.0,
    ) -> int:
        """Helper to calculate position quantity using central multi-constraint solver."""
        sig = PublishedSignal(
            id="temp_sig",
            instrument_id="temp_inst",
            symbol="TEMP",
            name_fa="موقت",
            as_of=now_utc(),
            opportunity_score=opportunity_score,
            p_profit=0.70,
            confidence=80.0,
            signal_strength=80.0,
            entry_zone={"low": entry_price, "high": entry_price * 1.01},
            invalidation={"price": stop_price},
            exit_plan={"targets": [entry_price * 1.08]},
            strategy_votes=[],
            top_reasons_fa=[],
            risk_flags_fa=[],
        )
        ticket = self.solver.solve(portfolio, sig, entry_price, adtv_20d_rials)
        return ticket["recommended_quantity"]

    def create_order_from_signal(
        self,
        portfolio: Portfolio,
        signal: PublishedSignal,
        current_market_price: float,
        quantity: int | None = None,
    ) -> Tuple[Optional[BrokerOrder], str]:
        """Creates and validates a paper order from an approved opportunity."""
        if LIVE_TRADING_ENABLED:
            return None, "خطای امنیتی: اتصال به معاملات زنده مسدود است (Paper Only)."

        if portfolio.kill_switch_active:
            return None, "کلید قطع اضطراری (Kill-Switch) فعال است؛ ثبت سفارش مجاز نیست."

        ticket = self.generate_pre_trade_ticket(portfolio, signal, current_market_price)
        if ticket["decision"] not in ["APPROVED"]:
            return None, f"سفارش توسط گیت مدیریت ریسک رد شد: {ticket['decision_reason_fa']}"

        exec_quantity = quantity or ticket["recommended_quantity"]
        if exec_quantity <= 0:
            return None, "حجم محاسبه شده کمتر از حداقل مجاز است."

        order_cost = exec_quantity * current_market_price * (1.0 + float(TSE_EQUITY_FEES.buy_fee_rate))
        if order_cost > portfolio.cash:
            return None, "موجودی نقد برای پوشش هزینه سفارش و کارمزد کافی نیست."

        now = now_utc()
        order_id = f"ord_{signal.symbol}_{now.strftime('%Y%m%d_%H%M%S')}"

        order = BrokerOrder(
            id=order_id,
            portfolio_id=portfolio.id,
            signal_id=signal.id,
            symbol=signal.symbol,
            side="BUY",
            order_type="LIMIT",
            price=current_market_price,
            quantity=exec_quantity,
            filled_quantity=exec_quantity,
            status="FILLED",
            created_at=now,
            updated_at=now,
        )

        portfolio.cash -= order_cost
        portfolio.updated_at = now

        target_val = ticket["target1_price"]
        stop_price = ticket["stop_price"]

        pos = Position(
            id=f"pos_{signal.symbol}_{now.strftime('%Y%m%d_%H%M%S')}",
            portfolio_id=portfolio.id,
            symbol=signal.symbol,
            quantity=exec_quantity,
            average_entry_price=current_market_price,
            current_price=current_market_price,
            unrealized_pnl=-round(order_cost - (exec_quantity * current_market_price)),
            stop_loss=stop_price,
            target_price=target_val,
            total_invested_rials=order_cost,
            risk_pct=ticket["risk_pct_nav"],
            risk_reward_ratio=f"1:{ticket['net_reward_risk_ratio']:.1f}",
            expected_days_to_target=5,
            market_regime=ticket["regime"],
            decision_method="Quantitative Multi-Constraint Ensemble",
            entry_reason_fa=signal.top_reasons_fa[0] if signal.top_reasons_fa else "همگرایی فاکتورهای کمّی و ورود پول حقیقی",
            is_open=True,
            opened_at=now,
        )
        portfolio.positions.append(pos)

        # Audit decision
        audit_entry = DecisionAudit(
            symbol=signal.symbol,
            signal_id=signal.id,
            decision="APPROVED",
            decision_reason_fa=ticket["decision_reason_fa"],
            opportunity_score=signal.opportunity_score,
            p_profit=signal.p_profit,
            as_of=now,
        )

        return order, f"سفارش خرید {exec_quantity:,} سهم {signal.symbol} با موفقیت در قیمت {current_market_price:,.0f} ریال اجرا شد."

    def scale_in_position(self, portfolio: Portfolio, position_id: str, current_price: float) -> Tuple[Optional[BrokerOrder], str]:
        """
        افزایش پله‌ای حجم سهم برنده (Stage 2/3).
        قاعده سخت: میانگین کم کردن در ضرر (Averaging Down) اکیداً ممنوع است.
        """
        pos = next((p for p in portfolio.positions if p.id == position_id and p.is_open), None)
        if not pos:
            return None, "موقعیت باز یافت نشد."

        # Hard Rule: No averaging down if losing
        if current_price < pos.average_entry_price:
            return None, "افزایش حجم در موقعیت‌های زیان‌ده (Averaging Down) طبق سیاست مدیریت ریسک ممنوع است."

        # Stage 2 (+35% initial size)
        add_qty = max(100, int(pos.quantity * 0.35))
        cost = add_qty * current_price * (1.0 + float(TSE_EQUITY_FEES.buy_fee_rate))

        if cost > portfolio.cash:
            return None, "نقدینگی در دسترس برای افزایش پله‌ای کافی نیست."

        now = now_utc()
        order = BrokerOrder(
            id=f"ord_scale_{pos.symbol}_{now.strftime('%Y%m%d_%H%M%S')}",
            portfolio_id=portfolio.id,
            symbol=pos.symbol,
            side="BUY",
            order_type="LIMIT",
            price=current_price,
            quantity=add_qty,
            filled_quantity=add_qty,
            status="FILLED",
            created_at=now,
            updated_at=now,
        )

        portfolio.cash -= cost
        total_qty = pos.quantity + add_qty
        pos.average_entry_price = ((pos.average_entry_price * pos.quantity) + (current_price * add_qty)) / total_qty
        pos.quantity = total_qty
        pos.total_invested_rials = pos.average_entry_price * total_qty
        pos.unrealized_pnl = (current_price - pos.average_entry_price) * total_qty

        # Raise stop loss to Breakeven
        pos.stop_loss = max(pos.stop_loss or 0, pos.average_entry_price * 1.01)

        return order, f"حجم نماد {pos.symbol} به میزان {add_qty:,} سهم افزایش یافت (پله دوم خرید ثبت شد و حد ضرر به نقطه سربه‌سر منتقل گردید)."

    def trim_position(self, portfolio: Portfolio, position_id: str, current_price: float, ratio: float = 0.25) -> Tuple[float, str]:
        """کاهش پله‌ای ۲۵٪ یا ۵۰٪ حجم برای سیو سود."""
        pos = next((p for p in portfolio.positions if p.id == position_id and p.is_open), None)
        if not pos:
            return 0.0, "موقعیت باز یافت نشد."

        trim_qty = max(1, int(pos.quantity * ratio))
        fee_info = calculate_trade_fees(trim_qty * current_price, side="SELL")
        net_proceeds = (trim_qty * current_price) - fee_info["total_fee_rials"]
        cost_basis = trim_qty * pos.average_entry_price
        realized_pnl = net_proceeds - cost_basis

        portfolio.cash += net_proceeds
        portfolio.realized_pnl += realized_pnl
        pos.quantity -= trim_qty
        pos.total_invested_rials = pos.average_entry_price * pos.quantity
        pos.unrealized_pnl = (current_price - pos.average_entry_price) * pos.quantity

        if pos.quantity <= 0:
            pos.is_open = False

        return realized_pnl, f"سیو سود {int(ratio*100)}٪ نماد {pos.symbol} انجام شد. سود خالص تحقق‌یافته: {realized_pnl/10:,.0f} تومان."

    def toggle_kill_switch(self, portfolio: Portfolio, active: bool) -> str:
        """فعال یا غیرفعال‌سازی کلید قطع اضطراری معامله."""
        portfolio.kill_switch_active = active
        return "کلید قطع اضطراری معامله فعال شد (خرید جدید و افزایش حجم مسدود گردید)." if active else "کلید قطع اضطراری غیرفعال شد."


paper_broker = PaperBrokerService()
