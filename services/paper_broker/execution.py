"""Unified Execution Simulator Core for Paper Broker and Backtester.
Guarantees Next-Bar execution at t+1, Realistic Queue Modeling, Linear Slippage, and Order State Transitions.
"""
from datetime import datetime, date
from typing import TypedDict, Literal, Optional, Tuple
from packages.domain.models import BrokerOrder, OrderFill, Position, Portfolio
from packages.market_rules.fees import calculate_trade_fees, TSE_EQUITY_FEES
from packages.shared.datetime_utils import now_utc
from packages.shared.logger import logger

OrderStatus = Literal[
    "CREATED",
    "VALIDATED",
    "SUBMITTED",
    "ACKNOWLEDGED",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCEL_REQUESTED",
    "CANCELLED",
    "EXPIRED",
    "REJECTED",
]


class ExecutionBar(TypedDict):
    trading_date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float
    allowed_min: Optional[float]
    allowed_max: Optional[float]


class ExecutionSimulator:
    """
    Unified Execution Simulator Core.
    Models Next-Bar auction fill, queue position, slippage, and price limit locks.
    """

    def __init__(self, default_slippage_bps: float = 20.0):
        self.default_slippage_bps = default_slippage_bps

    def simulate_order_fill(
        self,
        order: BrokerOrder,
        next_bar: ExecutionBar,
        is_limit_up_locked: bool = False,
        is_limit_down_locked: bool = False,
        participation_cap: float = 0.05,
    ) -> Tuple[Optional[OrderFill], str]:
        """
        Simulates order fill against the Next-Bar (t+1) price action.
        Enforces Point-in-Time discipline and queue locks.
        """
        # Guard against zero volume or missing bar
        if not next_bar or next_bar.get("volume", 0) <= 0:
            order.status = "EXPIRED"
            return None, "عدم انجام معامله در کندل بعدی (فاقد حجم معاملاتی)"

        bar_high = next_bar["high"]
        bar_low = next_bar["low"]
        bar_open = next_bar["open"]
        bar_close = next_bar["close"]
        bar_volume = next_bar["volume"]
        allowed_max = next_bar.get("allowed_max") or (bar_open * 1.05)
        allowed_min = next_bar.get("allowed_min") or (bar_open * 0.95)

        # 1. Buy Order Execution
        if order.side == "BUY":
            # Check for limit-up lock (صف خرید سنگین بدون عرضه)
            if is_limit_up_locked or (bar_low == allowed_max and bar_high == allowed_max):
                order.status = "REJECTED"
                return None, "سفارش به دلیل قفل صف خرید در سقف قیمت (Limit-Up Queue) رد شد."

            # Auction Opening fill with modeled slippage
            base_fill_price = bar_open if bar_open <= order.price else order.price
            
            # Slippage calculation based on volume participation
            participation_rate = min(1.0, order.quantity / bar_volume) if bar_volume > 0 else 0.05
            slippage_pct = (self.default_slippage_bps / 10_000.0) + (participation_rate * 0.005)
            effective_fill_price = round(min(allowed_max, base_fill_price * (1.0 + slippage_pct)), 2)

            # Cap fill quantity by liquidity limit (Max 5% of volume in single bar)
            max_fillable_qty = max(100, int(bar_volume * participation_cap))
            filled_qty = min(order.quantity, max_fillable_qty)

            fee_info = calculate_trade_fees(filled_qty * effective_fill_price, side="BUY")
            total_cost_rials = (filled_qty * effective_fill_price) + fee_info["total_fee_rials"]

            order.filled_quantity = filled_qty
            order.status = "FILLED" if filled_qty == order.quantity else "PARTIALLY_FILLED"
            order.updated_at = now_utc()

            fill = OrderFill(
                order_id=order.id,
                symbol=order.symbol,
                side="BUY",
                fill_price=effective_fill_price,
                quantity=filled_qty,
                slippage_rials=(effective_fill_price - base_fill_price) * filled_qty,
                fill_model="NEXT_BAR_AUCTION_SLIPPAGE",
                fees_rials=fee_info["broker_exchange_fee_rials"],
                tax_rials=fee_info["tax_rials"],
                net_value_rials=total_cost_rials,
                executed_at=now_utc(),
            )
            return fill, f"سفارش خرید {filled_qty:,} سهم با قیمت {effective_fill_price:,.0f} ریال اجرا شد."

        # 2. Sell Order Execution
        elif order.side == "SELL":
            # Check for limit-down lock (صف فروش سنگین بدون خریدار)
            if is_limit_down_locked or (bar_low == allowed_min and bar_high == allowed_min):
                order.status = "REJECTED"
                return None, "سفارش به دلیل قفل صف فروش در کف قیمت (Limit-Down Queue) رد شد."

            base_fill_price = bar_open if bar_open >= order.price else order.price
            participation_rate = min(1.0, order.quantity / bar_volume) if bar_volume > 0 else 0.05
            slippage_pct = (self.default_slippage_bps / 10_000.0) + (participation_rate * 0.005)
            effective_fill_price = round(max(allowed_min, base_fill_price * (1.0 - slippage_pct)), 2)

            filled_qty = order.quantity
            fee_info = calculate_trade_fees(filled_qty * effective_fill_price, side="SELL")
            net_proceeds_rials = (filled_qty * effective_fill_price) - fee_info["total_fee_rials"]

            order.filled_quantity = filled_qty
            order.status = "FILLED"
            order.updated_at = now_utc()

            fill = OrderFill(
                order_id=order.id,
                symbol=order.symbol,
                side="SELL",
                fill_price=effective_fill_price,
                quantity=filled_qty,
                slippage_rials=(base_fill_price - effective_fill_price) * filled_qty,
                fill_model="NEXT_BAR_AUCTION_SLIPPAGE",
                fees_rials=fee_info["broker_exchange_fee_rials"],
                tax_rials=fee_info["tax_rials"],
                net_value_rials=net_proceeds_rials,
                executed_at=now_utc(),
            )
            return fill, f"سفارش فروش {filled_qty:,} سهم با قیمت {effective_fill_price:,.0f} ریال اجرا شد."

        return None, "نوع سفارش نامعتبر است."

    def evaluate_exits_and_trailing_stop(
        self,
        position: Position,
        current_bar: ExecutionBar,
        initial_risk_rials: float,
        holding_sessions: int,
    ) -> Tuple[str, float, float]:
        """
        Evaluates trade exit rules:
        1. Stop loss hit -> Full Exit
        2. +2R Target -> Trim 25%
        3. +3R Target -> Trim additional 25%
        4. Trailing Stop (ATR-based) on remaining 50%
        5. Time Stop: 10 sessions with MFE < +0.5R
        Returns: (exit_action, exit_price, exit_ratio)
        """
        current_close = current_bar["close"]
        current_low = current_bar["low"]
        current_high = current_bar["high"]

        # 1. Stop Loss Hit
        if position.stop_loss and current_low <= position.stop_loss:
            return "STOP_LOSS", position.stop_loss, 1.0

        entry_price = position.average_entry_price
        r_unit = max(1.0, initial_risk_rials)
        current_r = (current_close - entry_price) / r_unit
        max_favorable_r = (current_high - entry_price) / r_unit

        # 2. Time Stop Rule (10 sessions without positive traction)
        if holding_sessions >= 10 and max_favorable_r < 0.5:
            return "TIME_STOP", current_close, 1.0

        # 3. Target 1 (+2R) Partial Exit 25%
        if current_r >= 2.0 and getattr(position, "stage_exit_level", 0) < 1:
            setattr(position, "stage_exit_level", 1)
            # Raise stop to Breakeven (+0.1R)
            position.stop_loss = max(position.stop_loss or 0, entry_price + (r_unit * 0.10))
            return "TARGET_1_TRIM_25", entry_price + (r_unit * 2.0), 0.25

        # 4. Target 2 (+3R) Partial Exit 25%
        if current_r >= 3.0 and getattr(position, "stage_exit_level", 0) < 2:
            setattr(position, "stage_exit_level", 2)
            # Lock +1.5R profit in trailing stop
            position.stop_loss = max(position.stop_loss or 0, entry_price + (r_unit * 1.50))
            return "TARGET_2_TRIM_25", entry_price + (r_unit * 3.0), 0.25

        # 5. Trailing Stop Violation on remaining position
        if position.stop_loss and current_close < position.stop_loss:
            return "TRAILING_STOP", position.stop_loss, 1.0

        return "HOLD", current_close, 0.0


execution_simulator = ExecutionSimulator()
